"""OpenAI-compatible synchronous vision transport and local response validation."""
import base64
import io
import json
import math
import os
import time
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageOps
from .pool import reserve


PROMPT = """Objetivo: catalogar referências visuais para comparar depois a geometria do CAD no FreeCAD.
A coleção é principalmente sobre o motor Fiat SEVEL SOHC 1.6 8V, com foco no Fiat Tipo 1.6 SPI de 82 cv.
Uma foto pode mostrar outra variante, uma peça avulsa, uma montagem, um desenho ou uma colagem.
Esse contexto não comprova a identidade da peça. Priorize contorno, aberturas, ressaltos e interfaces visíveis.
Descreva apenas o visível, em português. Não deduza medidas, material, variante ou função.
Separe observações de hipóteses. Use unknown ou not_visible quando necessário.
Em pranchas compare vistas, duplicatas, diferenças e conflitos sem presumir mesmo exemplar.
Retorne somente JSON com observations (lista de objetos com detail, seen_in: lista de
rótulos fornecidos, e opcional roi: [x0,y0,x1,y1] normalizada em uma única original),
classifications (lista com label, part, view, confidence entre 0 e 1), limitations (texto).
Em classifications, label deve ser um dos IDs de imagem fornecidos, por exemplo IMG-001.
Coloque a hipótese de peça em part. Use o mesmo label para várias peças visíveis na mesma foto."""

ENGLISH_PROMPT = """Create a visual parts-catalog entry for a reader who has never seen this part.
The catalog supports later FreeCAD geometry review. Most references concern the Fiat SEVEL SOHC
1.6 8V, especially the Fiat Tipo 1.6 SPI 82 cv. A picture can show another variant, a loose
part, an assembly, a drawing or a composite. Context is not proof of identity.
Write the catalog text in Portuguese. For each labeled image, start with the overall silhouette
and visible faces, then describe the arrangement of openings, bosses, ribs, flanges, recesses,
fasteners and surface markings where discernible. Use position relative to the image frame.
Include counts only when individually visible. Identify occlusions and edges hidden from view.
Give enough concrete detail to recognize the part from this angle. Do not fill gaps with typical
engine anatomy. Distinguish visible evidence from identity hypotheses; avoid unsupported material,
dimensions, function or absolute orientation. Use unknown or not_visible when appropriate.
For a sheet, explain what each view adds, what repeats and what conflicts. Verify each feature
in every frame cited. Return only JSON: observations (array of objects with detail and seen_in,
an array of supplied image labels; optional roi [x0,y0,x1,y1] normalized to one original);
classifications (array of objects with label, part, view and confidence from 0 to 1);
limitations (string). In classifications label is an image ID such as IMG-001. Put the part
hypothesis in part. Reuse a label for multiple visible components when needed."""


def roi_valid(box):
    return (isinstance(box, list) and len(box) == 4 and
            all(type(v) in (int, float) and math.isfinite(v) for v in box) and
            0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)


def validate(content, labels):
    # Accept one Markdown JSON fence surrounding the entire response.
    if isinstance(content, str):
        content = content.strip()
        if content.startswith("```json\n") and content.endswith("\n```"):
            content = content[8:-4]
    data = json.loads(content)
    if not isinstance(data, dict) or not isinstance(data.get("limitations"), str):
        raise ValueError("Missing limitations")
    obs = data.get("observations")
    if not isinstance(obs, list) or not obs:
        raise ValueError("Missing observations")
    for item in obs:
        if not isinstance(item, dict) or not isinstance(item.get("detail"), str) or not item["detail"].strip():
            raise ValueError("Missing visible detail")
        seen = item.get("seen_in")
        if not isinstance(seen, list) or not seen or any(v not in labels for v in seen):
            raise ValueError("Unknown observation support")
        if "roi" in item and (len(seen) != 1 or not roi_valid(item["roi"])):
            raise ValueError("Invalid ROI")
    if not isinstance(data.get("classifications"), list):
        raise ValueError("Missing classifications")
    for item in data["classifications"]:
        if (not isinstance(item, dict) or item.get("label") not in labels or
                not all(isinstance(item.get(k), str) and item[k].strip() for k in ("part","view")) or
                type(item.get("confidence")) not in (int,float) or not 0 <= item["confidence"] <= 1):
            raise ValueError("Invalid classification")
    return data


def payload(path, labels, config, provenance=None):
    with Image.open(path) as im:
        rgb = ImageOps.exif_transpose(im).convert("RGB")
    edge = config["max_image_edge_px"]
    rgb.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    rgb.save(stream, format="JPEG", quality=90)
    encoded = base64.b64encode(stream.getvalue()).decode("ascii")
    english = config.get("prompt_language") == "en"
    instruction = ENGLISH_PROMPT + "\nLabels: " if english else PROMPT + "\nRótulos: "
    content = [{"type":"text", "text":instruction + ", ".join(labels)},
               {"type":"image_url", "image_url":{"url":"data:image/jpeg;base64," + encoded}}]
    if provenance:
        note = ("Comparative pass. Source metadata for reconciliation only. Listing titles may be "
                "wrong. Identify which views add evidence.\n" if english else
                "Passagem comparativa. Metadados de origem de cada "
                        "quadro, apenas para conciliação. Nomes comerciais podem estar errados. "
                        "Informe quais vistas acrescentam evidência.\n")
        content.append({"type":"text","text":note + json.dumps(provenance, ensure_ascii=False)})
    body = dict(model=config["model"], stream=False, messages=[dict(role="user", content=content)])
    if len(json.dumps(body).encode()) > config["max_payload_bytes"]:
        raise ValueError("Payload exceeds configured limit")
    return body


def request_vision(session, body, config, remaining, record, sleep=time.sleep):
    url = config["base_url"].rstrip("/") + "/chat/completions"
    host = urlsplit(url).hostname
    headers = {}
    if host not in ("localhost","127.0.0.1","::1"):
        token = os.environ.get(config["api_key_env"])
        if host == "ollama.com" and not token:
            raise ValueError("Direct Ollama Cloud requires an API key; signin authorizes the local proxy")
        if token:
            if urlsplit(url).scheme != "https":
                raise ValueError("Bearer authentication requires HTTPS")
            headers["Authorization"] = "Bearer " + token
    for attempt in range(config["max_retries"] + 1):
        reserve(remaining)
        try:
            response = session.post(url, json=body, headers=headers, allow_redirects=False,
                                    timeout=(config["connect_timeout_s"], config["read_timeout_s"]))
        except requests.Timeout:
            record("uncertain", None, "timeout")
            return None
        except requests.RequestException as exc:
            record("error", None, type(exc).__name__)
            return None
        if response.status_code != 200:
            record("error", None, f"HTTP {response.status_code}")
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < config["max_retries"]:
                    delay = response.headers.get("Retry-After", "")
                    if delay and (not delay.isdigit() or int(delay) > 60):
                        return None
                    sleep(int(delay) if delay else min(2**attempt, 30))
                    continue
            return None
        response.raise_for_status()
        return response
