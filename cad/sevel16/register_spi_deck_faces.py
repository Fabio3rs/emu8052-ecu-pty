"""Register each casting's visible deck passages to the four-cylinder datum."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from config import ROOT, layout, load
from head_fixing_alignment import LANDMARKS, register
from register_spi_gasket import trace

# In the 1200 x 750 block photo the two webs are visible even where their
# shadows merge with the opening. Digitize each side of the web separately.
BLOCK = [
    [(191,305),(197,281),(220,281),(277,286),(275,298),(206,312)],
    [(315,274),(325,253),(381,251),(390,255),(388,298),(370,303),(327,292)],
    [(400,253),(447,254),(463,264),(461,282),(425,296),(397,300)],
    [(503,285),(515,277),(558,281),(565,295),(557,311),(530,308),(507,302)],
    [(584,290),(597,285),(604,294),(601,312),(588,313)],
    [(655,326),(661,305),(684,305),(731,293),(761,294),(760,307),(697,321),(673,335)],
    [(798,280),(808,263),(854,265),(862,273),(860,311),(844,312),(807,298)],
    [(873,268),(913,268),(934,278),(931,297),(890,312),(871,309)],
    [(971,298),(977,291),(1034,292),(1047,301),(1044,318),(1027,319),(973,308)],
    [(143,554),(150,538),(166,535),(216,562),(223,579),(210,589),(149,587)],
    [(279,572),(283,560),(346,531),(378,490),(390,491),(419,535),(464,558),
     (472,576),(462,583),(411,583),(395,556),(373,549),(354,555),(337,584),(289,583)],
    [(534,575),(541,559),(591,535),(623,487),(637,490),(670,534),(716,561),
     (720,579),(710,585),(660,585),(645,559),(624,549),(607,558),(593,584),(541,584)],
    [(782,576),(785,563),(838,533),(866,497),(878,503),(904,535),(905,552),
     (873,549),(855,557),(837,584),(789,585)],
    [(964,575),(974,567),(1012,566),(1024,576),(1022,597),(968,597)],
    [(1080,367),(1087,360),(1104,355),(1109,363),(1107,399),(1098,396)],
]

# Independent traces on the 1200 x 636 chamber-side head photo. Six tapered
# openings face the manifolds. Four oval mouths face the two large gasket windows.
HEAD = [
    [(185,242),(191,220),(254,218),(268,223),(263,237),(207,260),(190,255)],
    [(313,220),(379,214),(393,224),(392,247),(380,256),(317,232)],
    [(464,228),(472,214),(528,213),(538,219),(533,228),(487,249),(470,247)],
    [(578,215),(586,209),(643,209),(656,223),(659,241),(648,252),(632,251),(582,228)],
    [(707,218),(714,205),(765,204),(777,214),(774,222),(733,239),(713,236)],
    [(812,210),(823,205),(861,205),(873,216),(872,231),(861,236),(817,220)],
    [(982,194),(989,188),(1026,186),(1035,199),(1034,211),(983,213)],
    [(370,539),(379,520),(396,515),(410,523),(420,540),(412,562),(395,571),(375,558)],
    [(477,530),(484,512),(500,502),(515,511),(525,530),(518,551),(501,557),(483,548)],
    [(860,490),(867,471),(882,464),(897,478),(903,497),(894,515),(876,519),(861,507)],
    [(944,482),(951,462),(966,455),(979,468),(984,484),(977,505),(959,511),(946,500)],
    [(246,536),(250,523),(311,522),(323,531),(320,545),(258,554),(247,550)],
    [(573,505),(579,497),(617,487),(628,491),(630,506),(621,517),(581,522),(572,517)],
    [(778,482),(783,475),(822,475),(829,480),(826,495),(783,498)],
    [(1025,458),(1066,443),(1075,443),(1076,467),(1030,470),(1024,467)],
    [(1102,396),(1115,367),(1125,368),(1127,408),(1121,413),(1103,404)],
]


def casting(photo, controls, targets, profiles, circles):
    path, = (ROOT/"PhotosMotor").glob("*_"+photo+"-*.png")
    m, _ = cv2.findHomography(np.float64(controls),np.float64(targets))
    def project(points):
        return cv2.perspectiveTransform(np.float64([points]),m)[0]
    return {"source":str(path.relative_to(ROOT)), "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "control_px":controls, "control_mm":targets,
            "control_error_mm":np.linalg.norm(project(controls)-targets,axis=1).round(2).tolist(),
            "profiles_mm":[project(points).round(1).tolist() for points in profiles],
            "rounds":[[*project([(u,v)])[0].round(1),round(float(np.linalg.norm(
                project([(u+r,v)])[0]-project([(u-r,v)])[0])/2),1)] for u,v,r in circles]}


def run(output):
    xs = layout(*load())["centers"]
    landmarks = register(LANDMARKS["666447"],xs)
    block_points = [(254,435),(503,439),(749,445),(989,445),(390,276),(863,292),(998,584)]
    block_targets = [(x,0) for x in reversed(xs)] + list(reversed(landmarks["water_windows"])) + landmarks["opposite_end_slot"]
    head_points = [(139,226),(427,219),(679,213),(900,208),(1097,204),(179,533),(444,484),
                   (697,461),(920,440),(1106,440),(342,559),(548,536),(844,504),(1002,487)]
    head_targets = sum((landmarks[k][::-1] for k in ("opposite","plug_side","small")),[])
    data = {"gasket":trace(),
            "Block":casting("666661",block_points,block_targets,BLOCK,
                            [(129,504,10),(1096,506,9),(136,375,8),(384,376,8),(630,381,9),(867,384,8)]),
            "HeadLower":casting("704878",head_points,head_targets,HEAD,
                                [(148,309,13),(432,292,13),(684,281,13),(906,272,10),(1103,271,6),
                                 (152,459,10),(440,435,9),(694,415,9),(917,396,6)])}
    with output.open("x") as handle:
        json.dump(data,handle,indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    run(parser.parse_args().output)
