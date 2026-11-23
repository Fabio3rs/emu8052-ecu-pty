#include "../include/sdl_gpu_renderer.h"
#include "../include/shaders.h"

#include <SDL3/SDL.h>

#include <algorithm>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace {
// Must match the frame geometry arena in EngineSimApplication. In particular,
// the active oscilloscope set can exceed the old 100k/200k budget once the
// starter begins producing live sample traces.
constexpr int MaxVertices = 500000;
constexpr int MaxIndices = 1000000;

std::vector<std::uint8_t> loadBinaryFile(const std::string &path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) return {};
    const std::streamsize size = file.tellg();
    if (size <= 0) return {};
    std::vector<std::uint8_t> data(static_cast<size_t>(size));
    file.seekg(0);
    if (!file.read(reinterpret_cast<char *>(data.data()), size)) return {};
    return data;
}

SDL_GPUShaderFormat selectedShaderFormat(SDL_GPUDevice *device, const char **extension) {
    const SDL_GPUShaderFormat formats = SDL_GetGPUShaderFormats(device);
#if defined(__APPLE__)
    // SDL's Metal backend accepts portable MSL source directly. Prefer it on
    // Apple even if a compatibility backend happens to advertise SPIR-V.
    if ((formats & SDL_GPU_SHADERFORMAT_MSL) != 0) { *extension = "msl"; return SDL_GPU_SHADERFORMAT_MSL; }
#endif
    if ((formats & SDL_GPU_SHADERFORMAT_SPIRV) != 0) { *extension = "spv"; return SDL_GPU_SHADERFORMAT_SPIRV; }
    if ((formats & SDL_GPU_SHADERFORMAT_DXIL) != 0) { *extension = "dxil"; return SDL_GPU_SHADERFORMAT_DXIL; }
    if ((formats & SDL_GPU_SHADERFORMAT_MSL) != 0) { *extension = "msl"; return SDL_GPU_SHADERFORMAT_MSL; }
    *extension = nullptr;
    return SDL_GPU_SHADERFORMAT_INVALID;
}
}

SdlGpuRenderer::SdlGpuRenderer()
    : m_window(nullptr), m_windowClaimed(false), m_gpuDevice(nullptr), m_vertexBuffer(nullptr), m_indexBuffer(nullptr),
      m_vertexTransferBuffer(nullptr), m_indexTransferBuffer(nullptr), m_scenePipeline(nullptr),
      m_uiPipeline(nullptr), m_sceneTexture(nullptr), m_depthTexture(nullptr),
      m_sceneTextureWidth(0), m_sceneTextureHeight(0), m_depthTextureWidth(0), m_depthTextureHeight(0), m_vertices(nullptr),
      m_indices(nullptr), m_vertexCount(0), m_indexCount(0),
      m_clearColor(0.055f, 0.063f, 0.071f, 1.0f),
      m_sceneViewportX(0.0f), m_sceneViewportY(0.0f),
      m_sceneViewportWidth(0.0f), m_sceneViewportHeight(0.0f) { }
SdlGpuRenderer::~SdlGpuRenderer() { shutdown(); }

bool SdlGpuRenderer::initialize(void *nativeWindowHandle, const std::string &shaderDirectory, bool cadScene) {
    m_error.clear();
    m_cadScene = cadScene;
    m_window = nativeWindowHandle;
    if (m_window == nullptr) { m_error = "SDL window handle is null"; return false; }

    m_gpuDevice = SDL_CreateGPUDevice(
        SDL_GPU_SHADERFORMAT_SPIRV | SDL_GPU_SHADERFORMAT_DXIL | SDL_GPU_SHADERFORMAT_MSL,
        true,
        nullptr);
    if (m_gpuDevice == nullptr
        || !SDL_ClaimWindowForGPUDevice(m_gpuDevice, static_cast<SDL_Window *>(m_window))) {
        m_error = SDL_GetError();
        shutdown();
        return false;
    }
    m_windowClaimed = true;

    const SDL_GPUBufferCreateInfo vertexBufferInfo = {
        SDL_GPU_BUFFERUSAGE_VERTEX,
        static_cast<Uint32>(sizeof(EngineSimVertex) * MaxVertices),
        0
    };
    const SDL_GPUBufferCreateInfo indexBufferInfo = {
        SDL_GPU_BUFFERUSAGE_INDEX,
        static_cast<Uint32>(sizeof(std::uint16_t) * MaxIndices),
        0
    };
    const SDL_GPUTransferBufferCreateInfo vertexTransferInfo = {
        SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD,
        static_cast<Uint32>(sizeof(EngineSimVertex) * MaxVertices),
        0
    };
    const SDL_GPUTransferBufferCreateInfo indexTransferInfo = {
        SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD,
        static_cast<Uint32>(sizeof(std::uint16_t) * MaxIndices),
        0
    };
    if (!cadScene) {
        m_vertexBuffer = SDL_CreateGPUBuffer(m_gpuDevice, &vertexBufferInfo);
        m_indexBuffer = SDL_CreateGPUBuffer(m_gpuDevice, &indexBufferInfo);
        m_vertexTransferBuffer = SDL_CreateGPUTransferBuffer(m_gpuDevice, &vertexTransferInfo);
        m_indexTransferBuffer = SDL_CreateGPUTransferBuffer(m_gpuDevice, &indexTransferInfo);
        if (!m_vertexBuffer || !m_indexBuffer || !m_vertexTransferBuffer || !m_indexTransferBuffer) {
            m_error = SDL_GetError();
            shutdown();
            return false;
        }
    }

    const char *extension = nullptr;
    const SDL_GPUShaderFormat shaderFormat = selectedShaderFormat(m_gpuDevice, &extension);
    if (shaderFormat != SDL_GPU_SHADERFORMAT_INVALID) {
        const auto prefix = shaderDirectory + (cadScene ? "/sevel_cad." : "/engine_sim.");
        const std::vector<std::uint8_t> vertexCode = loadBinaryFile(
            prefix + "vertex." + extension);
        const std::vector<std::uint8_t> fragmentCode = loadBinaryFile(
            prefix + "fragment." + extension);
        if (!vertexCode.empty() && !fragmentCode.empty()) {
            // The offline shadercross CLI preserves the authored HLSL entry
            // point names for every emitted backend, including MSL.
            const char *vertexEntrypoint = "VSMain";
            const char *fragmentEntrypoint = "PSMain";
            const SDL_GPUShaderCreateInfo vertexInfo = {
                vertexCode.size(), vertexCode.data(), vertexEntrypoint, shaderFormat, SDL_GPU_SHADERSTAGE_VERTEX,
                0, 0, 0, 1, 0
            };
            const SDL_GPUShaderCreateInfo fragmentInfo = {
                fragmentCode.size(), fragmentCode.data(), fragmentEntrypoint, shaderFormat, SDL_GPU_SHADERSTAGE_FRAGMENT,
                0, 0, 0, 1, 0
            };
            SDL_GPUShader *vertexShader = SDL_CreateGPUShader(m_gpuDevice, &vertexInfo);
            SDL_GPUShader *fragmentShader = SDL_CreateGPUShader(m_gpuDevice, &fragmentInfo);
            if (vertexShader != nullptr && fragmentShader != nullptr) {
                const SDL_GPUVertexBufferDescription vertexBufferDescription = {
                    0, static_cast<Uint32>(sizeof(EngineSimVertex)), SDL_GPU_VERTEXINPUTRATE_VERTEX, 0
                };
                const SDL_GPUVertexAttribute vertexAttributes[] = {
                    { 0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4, static_cast<Uint32>(offsetof(EngineSimVertex, Pos)) },
                    { 1, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4, static_cast<Uint32>(offsetof(EngineSimVertex, Normal)) },
                    { 2, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, static_cast<Uint32>(offsetof(EngineSimVertex, TexCoord)) }
                };
                SDL_GPUColorTargetDescription colorTarget = {};
                colorTarget.format = SDL_GetGPUSwapchainTextureFormat(m_gpuDevice, static_cast<SDL_Window *>(m_window));
                colorTarget.blend_state.enable_blend = true;
                colorTarget.blend_state.src_color_blendfactor = SDL_GPU_BLENDFACTOR_SRC_ALPHA;
                colorTarget.blend_state.dst_color_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
                colorTarget.blend_state.color_blend_op = SDL_GPU_BLENDOP_ADD;
                colorTarget.blend_state.src_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
                colorTarget.blend_state.dst_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
                colorTarget.blend_state.alpha_blend_op = SDL_GPU_BLENDOP_ADD;
                SDL_GPUGraphicsPipelineCreateInfo pipelineInfo = {};
                pipelineInfo.vertex_shader = vertexShader;
                pipelineInfo.fragment_shader = fragmentShader;
                pipelineInfo.vertex_input_state = { &vertexBufferDescription, 1, vertexAttributes, 3 };
                pipelineInfo.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
                SDL_GPUTextureFormat depthFormat = SDL_GPU_TEXTUREFORMAT_D16_UNORM;
                if (cadScene) {
                    for (auto format : {SDL_GPU_TEXTUREFORMAT_D24_UNORM_S8_UINT,SDL_GPU_TEXTUREFORMAT_D32_FLOAT_S8_UINT}) {
                        if (SDL_GPUTextureSupportsFormat(m_gpuDevice,format,SDL_GPU_TEXTURETYPE_2D,
                                                        SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET)) {
                            depthFormat = format;
                            break;
                        }
                    }
                }
                m_depthFormat = static_cast<std::uint32_t>(depthFormat);
                pipelineInfo.target_info = { &colorTarget, 1, depthFormat, cadScene, 0, 0, 0 };
                pipelineInfo.depth_stencil_state.enable_depth_test = true;
                pipelineInfo.depth_stencil_state.enable_depth_write = true;
                pipelineInfo.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_LESS_OR_EQUAL;
                if (cadScene) {
                    pipelineInfo.rasterizer_state.front_face = SDL_GPU_FRONTFACE_COUNTER_CLOCKWISE;
                    pipelineInfo.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_BACK;
                }
                m_scenePipeline = SDL_CreateGPUGraphicsPipeline(m_gpuDevice, &pipelineInfo);
                if (cadScene) {
                    pipelineInfo.depth_stencil_state.enable_depth_write = false;
                    m_transparentPipeline = SDL_CreateGPUGraphicsPipeline(m_gpuDevice,&pipelineInfo);
                    pipelineInfo.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_NONE;
                }
                if (depthFormat != SDL_GPU_TEXTUREFORMAT_D16_UNORM) {
                    auto &depth = pipelineInfo.depth_stencil_state;
                    depth.enable_stencil_test = true;
                    depth.compare_mask = depth.write_mask = 1;
                    depth.front_stencil_state = depth.back_stencil_state = {SDL_GPU_STENCILOP_KEEP,
                        SDL_GPU_STENCILOP_INVERT, SDL_GPU_STENCILOP_KEEP, SDL_GPU_COMPAREOP_ALWAYS};
                    depth.enable_depth_write = depth.enable_depth_test = false;
                    colorTarget.blend_state.enable_color_write_mask = true;
                    colorTarget.blend_state.color_write_mask = 0;
                    m_parityPipeline = SDL_CreateGPUGraphicsPipeline(m_gpuDevice, &pipelineInfo);
                    colorTarget.blend_state.enable_color_write_mask = false;
                    depth.front_stencil_state = depth.back_stencil_state = {SDL_GPU_STENCILOP_KEEP,
                        SDL_GPU_STENCILOP_KEEP, SDL_GPU_STENCILOP_KEEP, SDL_GPU_COMPAREOP_NOT_EQUAL};
                    depth.enable_depth_test = depth.enable_depth_write = true;
                    depth.write_mask = 0;
                    m_capPipeline = SDL_CreateGPUGraphicsPipeline(m_gpuDevice, &pipelineInfo);
                }

                pipelineInfo.target_info.depth_stencil_format = SDL_GPU_TEXTUREFORMAT_INVALID;
                pipelineInfo.target_info.has_depth_stencil_target = false;
                pipelineInfo.depth_stencil_state = {};
                m_uiPipeline = SDL_CreateGPUGraphicsPipeline(m_gpuDevice, &pipelineInfo);
                if (m_scenePipeline == nullptr || m_uiPipeline == nullptr) m_error = SDL_GetError();
            }
            else m_error = SDL_GetError();
            if (vertexShader != nullptr) SDL_ReleaseGPUShader(m_gpuDevice, vertexShader);
            if (fragmentShader != nullptr) SDL_ReleaseGPUShader(m_gpuDevice, fragmentShader);
        }
        else m_error = "Missing SDL GPU shader artifacts in " + shaderDirectory
            + "; install SDL_shadercross and rebuild engine-sim-desktop";
    }
    else m_error = SDL_GetError();
    if (m_scenePipeline == nullptr || m_uiPipeline == nullptr || (cadScene && !m_transparentPipeline)) {
        if (m_error.empty()) m_error = "SDL GPU graphics pipeline creation failed";
        shutdown();
        return false;
    }
    return true;
}

void SdlGpuRenderer::shutdown() {
    if (m_gpuDevice != nullptr) {
        if (m_background) SDL_ReleaseGPUTexture(m_gpuDevice,m_background);
        if (m_backgroundTransfer) SDL_ReleaseGPUTransferBuffer(m_gpuDevice,m_backgroundTransfer);
        m_background = nullptr;
        m_backgroundTransfer = nullptr;
        m_backgroundWidth = m_backgroundHeight = 0;
        if (m_parityPipeline) SDL_ReleaseGPUGraphicsPipeline(m_gpuDevice,m_parityPipeline);
        if (m_transparentPipeline) SDL_ReleaseGPUGraphicsPipeline(m_gpuDevice,m_transparentPipeline);
        m_transparentPipeline = nullptr;
        if (m_capPipeline) SDL_ReleaseGPUGraphicsPipeline(m_gpuDevice,m_capPipeline);
        m_parityPipeline = m_capPipeline = nullptr;
        if (m_staticVertices) SDL_ReleaseGPUBuffer(m_gpuDevice, m_staticVertices);
        if (m_staticIndices) SDL_ReleaseGPUBuffer(m_gpuDevice, m_staticIndices);
        m_staticVertices = nullptr;
        m_staticIndices = nullptr;
        if (m_scenePipeline != nullptr) SDL_ReleaseGPUGraphicsPipeline(m_gpuDevice, m_scenePipeline);
        if (m_uiPipeline != nullptr) SDL_ReleaseGPUGraphicsPipeline(m_gpuDevice, m_uiPipeline);
        if (m_sceneTexture != nullptr) SDL_ReleaseGPUTexture(m_gpuDevice, m_sceneTexture);
        if (m_depthTexture != nullptr) SDL_ReleaseGPUTexture(m_gpuDevice, m_depthTexture);
        if (m_vertexTransferBuffer != nullptr) SDL_ReleaseGPUTransferBuffer(m_gpuDevice, m_vertexTransferBuffer);
        if (m_indexTransferBuffer != nullptr) SDL_ReleaseGPUTransferBuffer(m_gpuDevice, m_indexTransferBuffer);
        if (m_vertexBuffer != nullptr) SDL_ReleaseGPUBuffer(m_gpuDevice, m_vertexBuffer);
        if (m_indexBuffer != nullptr) SDL_ReleaseGPUBuffer(m_gpuDevice, m_indexBuffer);
        m_vertexTransferBuffer = nullptr;
        m_indexTransferBuffer = nullptr;
        m_vertexBuffer = nullptr;
        m_indexBuffer = nullptr;
        m_scenePipeline = nullptr;
        m_uiPipeline = nullptr;
        m_sceneTexture = nullptr;
        m_depthTexture = nullptr;
        m_sceneTextureWidth = 0;
        m_sceneTextureHeight = 0;
        m_depthTextureWidth = 0;
        m_depthTextureHeight = 0;
        if (m_windowClaimed && m_window != nullptr) {
            SDL_ReleaseWindowFromGPUDevice(m_gpuDevice, static_cast<SDL_Window *>(m_window));
        }
        m_windowClaimed = false;
        SDL_DestroyGPUDevice(m_gpuDevice);
        m_gpuDevice = nullptr;
    }
    m_window = nullptr;
}

void SdlGpuRenderer::beginFrame(const ysVector &clearColor) {
    m_clearColor = clearColor;
    m_vertices = nullptr;
    m_indices = nullptr;
    m_vertexCount = 0;
    m_indexCount = 0;
    m_submissions.clear();
    m_sections.clear();
}

void SdlGpuRenderer::endSectionPart(std::size_t firstDraw, int quadVertex, int quadIndex,
                                    const ysMatrix &planeModel, bool second) {
    if (!supportsSectionCaps() || firstDraw >= m_submissions.size()) return;
    auto plane = m_submissions[firstDraw];
    plane.baseVertex = quadVertex;
    plane.baseIndex = quadIndex;
    plane.faceCount = 2;
    plane.transform = planeModel;
    const auto parity = second ? plane.secondPlane : plane.clipPlane;
    plane.clipPlane = second ? plane.clipPlane : plane.secondPlane;
    plane.secondPlane = plane.deformation = {};
    plane.color = {.94f,.48f,.21f,1};
    m_sections.push_back({firstDraw,m_submissions.size(),plane,parity});
}

void SdlGpuRenderer::profileScene(std::uint64_t frameStart) {
    if (!SDL_GetEnvironmentVariable(SDL_GetEnvironment(),"SEVEL_CAD_PROFILE")) return;
    SDL_WaitForGPUIdle(m_gpuDevice);
    const double ms = static_cast<double>(SDL_GetPerformanceCounter()-frameStart)*1000 /
                      static_cast<double>(SDL_GetPerformanceFrequency());
    if (++m_profileFrames <= 2) {
        m_profileStart = SDL_GetPerformanceCounter();
        return;
    }
    m_profileMs += ms;
    if (m_profileFrames == 12 || m_profileFrames%60 == 0) {
        std::size_t draws = m_submissions.size(), tris = 0;
        for (auto &s : m_submissions) tris += static_cast<std::size_t>(s.faceCount);
        for (auto &s : m_sections) {
            draws += s.end-s.first+1;
            tris += 2;
            for (auto i=s.first; i<s.end; ++i) tris += static_cast<std::size_t>(m_submissions[i].faceCount);
        }
        const double elapsed = static_cast<double>(SDL_GetPerformanceCounter()-m_profileStart) /
                               static_cast<double>(SDL_GetPerformanceFrequency());
        std::printf("[LAB-CAD-PERF] backend=%s resolution=%ux%u frames=%u draws=%zu triangles=%zu caps=%zu render_gpu_ms=%.3f lab_fps=%.2f\n",
            SDL_GetGPUDeviceDriver(m_gpuDevice),m_sceneTextureWidth,m_sceneTextureHeight,m_profileFrames-2,
            draws,tris,m_sections.size(),m_profileMs/(m_profileFrames-2),(m_profileFrames-2)/elapsed);
    }
}

void SdlGpuRenderer::setSceneViewport(float x, float y, float width, float height) {
    m_sceneViewportX = x;
    m_sceneViewportY = y;
    m_sceneViewportWidth = std::max(0.0f, width);
    m_sceneViewportHeight = std::max(0.0f, height);
}

bool SdlGpuRenderer::installStaticGeometry(const std::vector<EngineSimVertex> &vertices,
                                           const std::vector<std::uint16_t> &indices,
                                           std::string &error) {
    const size_t vb = vertices.size() * sizeof(EngineSimVertex);
    const size_t ib = indices.size() * sizeof(std::uint16_t);
    if (!m_gpuDevice || !vb || !ib || vb + ib > 512u*1024*1024) {
        error = "Invalid static geometry size";
        return false;
    }
    const SDL_GPUBufferCreateInfo vi{SDL_GPU_BUFFERUSAGE_VERTEX, static_cast<Uint32>(vb), 0};
    const SDL_GPUBufferCreateInfo ii{SDL_GPU_BUFFERUSAGE_INDEX, static_cast<Uint32>(ib), 0};
    const SDL_GPUTransferBufferCreateInfo ti{SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD, static_cast<Uint32>(vb+ib), 0};
    auto *v = SDL_CreateGPUBuffer(m_gpuDevice, &vi);
    auto *i = SDL_CreateGPUBuffer(m_gpuDevice, &ii);
    auto *transfer = SDL_CreateGPUTransferBuffer(m_gpuDevice, &ti);
    bool ready = false;
    if (v && i && transfer) {
        if (auto *memory = static_cast<unsigned char *>(SDL_MapGPUTransferBuffer(m_gpuDevice, transfer, false))) {
            std::memcpy(memory, vertices.data(), vb);
            std::memcpy(memory+vb, indices.data(), ib);
            SDL_UnmapGPUTransferBuffer(m_gpuDevice, transfer);
            if (auto *commands = SDL_AcquireGPUCommandBuffer(m_gpuDevice)) {
                if (auto *pass = SDL_BeginGPUCopyPass(commands)) {
                    const SDL_GPUTransferBufferLocation vs{transfer,0}, is{transfer,static_cast<Uint32>(vb)};
                    const SDL_GPUBufferRegion vd{v,0,vi.size}, id{i,0,ii.size};
                    SDL_UploadToGPUBuffer(pass,&vs,&vd,false);
                    SDL_UploadToGPUBuffer(pass,&is,&id,false);
                    SDL_EndGPUCopyPass(pass);
                    ready = SDL_SubmitGPUCommandBuffer(commands) && SDL_WaitForGPUIdle(m_gpuDevice);
                } else SDL_CancelGPUCommandBuffer(commands);
            }
        }
    }
    if (ready) {
        std::swap(v, m_staticVertices);
        std::swap(i, m_staticIndices);
    } else error = SDL_GetError();
    if (transfer) SDL_ReleaseGPUTransferBuffer(m_gpuDevice, transfer);
    if (v) SDL_ReleaseGPUBuffer(m_gpuDevice, v);
    if (i) SDL_ReleaseGPUBuffer(m_gpuDevice, i);
    return ready;
}

void SdlGpuRenderer::uploadGeometry(
    const EngineSimVertex *vertices,
    int vertexCount,
    const std::uint16_t *indices,
    int indexCount)
{
    if (m_cadScene || vertexCount < 0 || vertexCount > MaxVertices || indexCount < 0 || indexCount > MaxIndices) return;
    m_vertices = vertices;
    m_indices = indices;
    m_vertexCount = vertexCount;
    m_indexCount = indexCount;
}

void SdlGpuRenderer::submitGeometry(
    const EngineSimVertex *,
    const std::uint16_t *,
    int baseVertex,
    int baseIndex,
    int faceCount,
    const ysMatrix &transform,
    const ysMatrix &cameraView,
    const ysMatrix &projection,
    const ysVector &color,
    std::uint32_t stage,
    int layer)
{
    m_submissions.push_back({ baseVertex, baseIndex, faceCount,
        transform, cameraView, projection, color, m_clipPlane, m_secondPlane, m_deformation, stage, layer });
}

void SdlGpuRenderer::endFrame() {
    if (m_gpuDevice == nullptr || m_window == nullptr) return;

    SDL_GPUCommandBuffer *commands = SDL_AcquireGPUCommandBuffer(m_gpuDevice);
    if (commands == nullptr) { m_error = SDL_GetError(); return; }

    if (m_vertexCount > 0 && m_indexCount > 0) {
        void *vertexUpload = SDL_MapGPUTransferBuffer(m_gpuDevice, m_vertexTransferBuffer, true);
        void *indexUpload = SDL_MapGPUTransferBuffer(m_gpuDevice, m_indexTransferBuffer, true);
        if (vertexUpload == nullptr || indexUpload == nullptr) {
            m_error = SDL_GetError();
            if (vertexUpload != nullptr) SDL_UnmapGPUTransferBuffer(m_gpuDevice, m_vertexTransferBuffer);
            if (indexUpload != nullptr) SDL_UnmapGPUTransferBuffer(m_gpuDevice, m_indexTransferBuffer);
            SDL_CancelGPUCommandBuffer(commands);
            return;
        }
        std::memcpy(vertexUpload, m_vertices, sizeof(EngineSimVertex) * static_cast<size_t>(m_vertexCount));
        std::memcpy(indexUpload, m_indices, sizeof(std::uint16_t) * static_cast<size_t>(m_indexCount));
        SDL_UnmapGPUTransferBuffer(m_gpuDevice, m_vertexTransferBuffer);
        SDL_UnmapGPUTransferBuffer(m_gpuDevice, m_indexTransferBuffer);

        SDL_GPUCopyPass *copyPass = SDL_BeginGPUCopyPass(commands);
        if (copyPass == nullptr) {
            m_error = SDL_GetError();
            SDL_CancelGPUCommandBuffer(commands);
            return;
        }
        const SDL_GPUTransferBufferLocation vertexSource = { m_vertexTransferBuffer, 0 };
        const SDL_GPUTransferBufferLocation indexSource = { m_indexTransferBuffer, 0 };
        const SDL_GPUBufferRegion vertexDestination = {
            m_vertexBuffer, 0, static_cast<Uint32>(sizeof(EngineSimVertex) * m_vertexCount)
        };
        const SDL_GPUBufferRegion indexDestination = {
            m_indexBuffer, 0, static_cast<Uint32>(sizeof(std::uint16_t) * m_indexCount)
        };
        SDL_UploadToGPUBuffer(copyPass, &vertexSource, &vertexDestination, true);
        SDL_UploadToGPUBuffer(copyPass, &indexSource, &indexDestination, true);
        SDL_EndGPUCopyPass(copyPass);
    }

    SDL_GPUTexture *swapchainTexture = nullptr;
    Uint32 swapchainWidth = 0;
    Uint32 swapchainHeight = 0;
    if (!SDL_WaitAndAcquireGPUSwapchainTexture(
            commands, static_cast<SDL_Window *>(m_window), &swapchainTexture,
            &swapchainWidth, &swapchainHeight)) {
        m_error = SDL_GetError();
        SDL_CancelGPUCommandBuffer(commands);
        return;
    }

    if (swapchainTexture != nullptr) {
        const Uint32 sceneX = static_cast<Uint32>(
            std::clamp(m_sceneViewportX, 0.0f, static_cast<float>(swapchainWidth)));
        const Uint32 sceneY = static_cast<Uint32>(
            std::clamp(m_sceneViewportY, 0.0f, static_cast<float>(swapchainHeight)));
        if (sceneX >= swapchainWidth || sceneY >= swapchainHeight) {
            SDL_SubmitGPUCommandBuffer(commands);
            return;
        }
        const Uint32 sceneWidth = std::min(swapchainWidth - sceneX,
            std::max(1u, static_cast<Uint32>(m_sceneViewportWidth)));
        const Uint32 sceneHeight = std::min(swapchainHeight - sceneY,
            std::max(1u, static_cast<Uint32>(m_sceneViewportHeight)));
        if (m_sceneTexture == nullptr || m_sceneTextureWidth != sceneWidth || m_sceneTextureHeight != sceneHeight) {
            if (m_sceneTexture != nullptr) SDL_ReleaseGPUTexture(m_gpuDevice, m_sceneTexture);
            const SDL_GPUTextureCreateInfo sceneInfo = { SDL_GPU_TEXTURETYPE_2D,
                SDL_GetGPUSwapchainTextureFormat(m_gpuDevice, static_cast<SDL_Window *>(m_window)),
                SDL_GPU_TEXTUREUSAGE_COLOR_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER,
                sceneWidth, sceneHeight, 1, 1, SDL_GPU_SAMPLECOUNT_1, 0 };
            m_sceneTexture = SDL_CreateGPUTexture(m_gpuDevice, &sceneInfo);
            m_sceneTextureWidth = sceneWidth;
            m_sceneTextureHeight = sceneHeight;
        }
        if (m_depthTexture == nullptr || m_depthTextureWidth != sceneWidth || m_depthTextureHeight != sceneHeight) {
            if (m_depthTexture != nullptr) SDL_ReleaseGPUTexture(m_gpuDevice, m_depthTexture);
            const SDL_GPUTextureCreateInfo depthInfo = {
                SDL_GPU_TEXTURETYPE_2D, static_cast<SDL_GPUTextureFormat>(m_depthFormat),
                SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET, sceneWidth, sceneHeight,
                1, 1, SDL_GPU_SAMPLECOUNT_1, 0
            };
            m_depthTexture = SDL_CreateGPUTexture(m_gpuDevice, &depthInfo);
            m_depthTextureWidth = sceneWidth;
            m_depthTextureHeight = sceneHeight;
        }
        if (m_sceneTexture == nullptr || m_depthTexture == nullptr) {
            m_error = SDL_GetError();
            SDL_SubmitGPUCommandBuffer(commands);
            return;
        }

        const auto drawOne = [&](SDL_GPURenderPass *pass, const Submission *submission) {
                struct VertexUniforms { ysMatrix matrices[3]; ysVector deformation; };
                const VertexUniforms transforms = {{
                    submission->transform,
                    submission->cameraView,
                    submission->projection
                },submission->deformation};
                SDL_PushGPUVertexUniformData(commands, 0, &transforms, m_cadScene ? sizeof(transforms) : sizeof(transforms.matrices));
                const ysVector surface[] = {submission->color, submission->clipPlane, submission->secondPlane};
                SDL_PushGPUFragmentUniformData(commands, 0, surface, m_cadScene ? sizeof(surface) : sizeof(ysVector));
                SDL_DrawGPUIndexedPrimitives(pass, static_cast<Uint32>(submission->faceCount * 3), 1,
                    static_cast<Uint32>(submission->baseIndex), submission->baseVertex, 0);
        };
        const auto drawStage = [&](SDL_GPURenderPass *pass, std::uint32_t stage, bool transparent=false) {
            std::vector<const Submission *> submissions;
            for (const Submission &submission : m_submissions) {
                if ((submission.stage & stage) != 0 &&
                    (!m_staticVertices || (submission.color.w < 1.f) == transparent))
                    submissions.push_back(&submission);
            }
            std::stable_sort(submissions.begin(), submissions.end(),
                [](const Submission *left, const Submission *right) { return left->layer < right->layer; });
            for (const Submission *submission : submissions) drawOne(pass,submission);
        };
        const auto bindGeometry = [&](SDL_GPURenderPass *pass, SDL_GPUGraphicsPipeline *pipeline) {
            SDL_BindGPUGraphicsPipeline(pass, pipeline);
            const SDL_GPUBufferBinding vertexBinding = { m_staticVertices ? m_staticVertices : m_vertexBuffer, 0 };
            const SDL_GPUBufferBinding indexBinding = { m_staticIndices ? m_staticIndices : m_indexBuffer, 0 };
            SDL_BindGPUVertexBuffers(pass, 0, &vertexBinding, 1);
            SDL_BindGPUIndexBuffer(pass, &indexBinding, SDL_GPU_INDEXELEMENTSIZE_16BIT);
        };

        SDL_GPUColorTargetInfo sceneColorTarget = {};
        sceneColorTarget.texture = m_sceneTexture;
        sceneColorTarget.clear_color = { m_clearColor.x, m_clearColor.y, m_clearColor.z, m_clearColor.w };
        sceneColorTarget.load_op = SDL_GPU_LOADOP_CLEAR;
        sceneColorTarget.store_op = SDL_GPU_STOREOP_STORE;
        SDL_GPUDepthStencilTargetInfo depthTarget = {};
        depthTarget.texture = m_depthTexture;
        depthTarget.clear_depth = 1.0f;
        depthTarget.load_op = SDL_GPU_LOADOP_CLEAR;
        const bool hasTransparent = m_staticVertices && std::any_of(m_submissions.begin(),m_submissions.end(),
            [](const auto &s) { return s.color.w < 1.f; });
        depthTarget.store_op = m_sections.empty() && !hasTransparent ? SDL_GPU_STOREOP_DONT_CARE : SDL_GPU_STOREOP_STORE;
        depthTarget.stencil_load_op = SDL_GPU_LOADOP_DONT_CARE;
        depthTarget.stencil_store_op = SDL_GPU_STOREOP_DONT_CARE;
        SDL_GPUColorTargetInfo clearTarget = sceneColorTarget;
        clearTarget.texture = swapchainTexture;
        SDL_GPURenderPass *clearPass = SDL_BeginGPURenderPass(commands, &clearTarget, 1, nullptr);
        if (clearPass == nullptr) {
            m_error = SDL_GetError();
            SDL_SubmitGPUCommandBuffer(commands);
            return;
        }
        SDL_EndGPURenderPass(clearPass);
        if (m_background) {
            const SDL_GPUBlitInfo backgroundBlit = {
                {m_background,0,0,0,0,m_backgroundWidth,m_backgroundHeight},
                {swapchainTexture,0,0,0,0,swapchainWidth,swapchainHeight},
                SDL_GPU_LOADOP_LOAD,{},SDL_FLIP_NONE,SDL_GPU_FILTER_NEAREST,false,0,0,0};
            SDL_BlitGPUTexture(commands,&backgroundBlit);
            if (m_submissions.empty()) {
                if (!SDL_SubmitGPUCommandBuffer(commands)) m_error = SDL_GetError();
                return;
            }
        }
        SDL_GPURenderPass *scenePass = SDL_BeginGPURenderPass(commands, &sceneColorTarget, 1,
            m_depthTexture != nullptr ? &depthTarget : nullptr);
        if (scenePass == nullptr) {
            m_error = SDL_GetError();
            SDL_SubmitGPUCommandBuffer(commands);
            return;
        }
        if (m_scenePipeline != nullptr && (m_staticVertices || (m_vertexCount > 0 && m_indexCount > 0))) {
            bindGeometry(scenePass, m_scenePipeline);
            if (m_sceneViewportWidth > 0.0f && m_sceneViewportHeight > 0.0f) {
                const SDL_GPUViewport sceneViewport = { 0.0f, 0.0f,
                    static_cast<float>(sceneWidth), static_cast<float>(sceneHeight), 0.0f, 1.0f };
                SDL_SetGPUViewport(scenePass, &sceneViewport);
            }
            drawStage(scenePass, Shaders::SceneStage);
        }
        SDL_EndGPURenderPass(scenePass);

        // Odd coverage of the clipped closed surface projects exactly the
        // section interior. Clear parity per solid so nested holes and
        // disjoint solids retain their own topology.
        for (const auto &section : m_sections) {
            sceneColorTarget.load_op = SDL_GPU_LOADOP_LOAD;
            depthTarget.load_op = SDL_GPU_LOADOP_LOAD;
            depthTarget.stencil_load_op = SDL_GPU_LOADOP_CLEAR;
            auto *pass = SDL_BeginGPURenderPass(commands,&sceneColorTarget,1,&depthTarget);
            if (!pass) { m_error = SDL_GetError(); break; }
            SDL_SetGPUStencilReference(pass,0);
            bindGeometry(pass,m_parityPipeline);
            for (auto i=section.first; i<section.end; ++i) {
                auto clipped = m_submissions[i];
                clipped.clipPlane = section.parityPlane;
                clipped.secondPlane = {};
                drawOne(pass,&clipped);
            }
            SDL_BindGPUGraphicsPipeline(pass,m_capPipeline);
            drawOne(pass,&section.plane);
            SDL_EndGPURenderPass(pass);
        }

        if (hasTransparent) {
            sceneColorTarget.load_op = depthTarget.load_op = SDL_GPU_LOADOP_LOAD;
            depthTarget.stencil_load_op = SDL_GPU_LOADOP_DONT_CARE;
            auto *pass = SDL_BeginGPURenderPass(commands,&sceneColorTarget,1,&depthTarget);
            if (pass) {
                bindGeometry(pass,m_transparentPipeline);
                drawStage(pass,Shaders::SceneStage,true);
                SDL_EndGPURenderPass(pass);
            } else m_error = SDL_GetError();
        }
        if (m_sceneTexture != nullptr) {
            const SDL_GPUBlitInfo blitInfo = {
                { m_sceneTexture, 0, 0, 0, 0, sceneWidth, sceneHeight },
                { swapchainTexture, 0, 0, sceneX, sceneY, sceneWidth, sceneHeight },
                SDL_GPU_LOADOP_LOAD, {}, SDL_FLIP_NONE, SDL_GPU_FILTER_LINEAR, false, 0, 0, 0
            };
            SDL_BlitGPUTexture(commands, &blitInfo);
        }

        SDL_GPUColorTargetInfo uiColorTarget = sceneColorTarget;
        uiColorTarget.texture = swapchainTexture;
        uiColorTarget.load_op = SDL_GPU_LOADOP_LOAD;
        SDL_GPURenderPass *uiPass = SDL_BeginGPURenderPass(commands, &uiColorTarget, 1, nullptr);
        if (uiPass == nullptr) {
            m_error = SDL_GetError();
            SDL_SubmitGPUCommandBuffer(commands);
            return;
        }
        if (m_uiPipeline != nullptr && m_vertexCount > 0 && m_indexCount > 0) {
            bindGeometry(uiPass, m_uiPipeline);
            drawStage(uiPass, Shaders::UiStage);
        }
        SDL_EndGPURenderPass(uiPass);
    }
    if (!SDL_SubmitGPUCommandBuffer(commands)) m_error = SDL_GetError();
}

bool SdlGpuRenderer::captureSceneRgba(std::vector<std::uint8_t> &pixels,
                                      std::uint32_t &width, std::uint32_t &height,
                                      std::string &error) {
    pixels.clear();
    width = height = 0;
    error.clear();
    if (m_gpuDevice == nullptr || m_sceneTexture == nullptr || !m_error.empty()) {
        error = "GPU scene is unavailable";
        return false;
    }
    const auto format = SDL_GetGPUSwapchainTextureFormat(
        m_gpuDevice, static_cast<SDL_Window *>(m_window));
    const bool bgra = format == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM ||
                      format == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM_SRGB;
    const bool rgba = format == SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM ||
                      format == SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM_SRGB;
    const auto bytes = SDL_CalculateGPUTextureFormatSize(
        format, m_sceneTextureWidth, m_sceneTextureHeight, 1);
    if ((!bgra && !rgba) || bytes == 0 ||
        bytes != std::uint64_t(m_sceneTextureWidth) * m_sceneTextureHeight * 4) {
        error = "GPU scene format cannot be captured as RGBA8";
        return false;
    }
    if (!SDL_WaitForGPUIdle(m_gpuDevice)) {
        error = SDL_GetError();
        return false;
    }
    const SDL_GPUTransferBufferCreateInfo info = {
        SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD, bytes, 0};
    SDL_GPUTransferBuffer *transfer = SDL_CreateGPUTransferBuffer(m_gpuDevice, &info);
    if (transfer == nullptr) {
        error = SDL_GetError();
        return false;
    }
    SDL_GPUCommandBuffer *commands = SDL_AcquireGPUCommandBuffer(m_gpuDevice);
    if (commands == nullptr) {
        error = SDL_GetError();
        SDL_ReleaseGPUTransferBuffer(m_gpuDevice, transfer);
        return false;
    }
    SDL_GPUCopyPass *pass = SDL_BeginGPUCopyPass(commands);
    if (pass == nullptr) {
        error = SDL_GetError();
        SDL_CancelGPUCommandBuffer(commands);
        SDL_ReleaseGPUTransferBuffer(m_gpuDevice, transfer);
        return false;
    }
    const SDL_GPUTextureRegion source = {
        m_sceneTexture, 0, 0, 0, 0, 0,
        m_sceneTextureWidth, m_sceneTextureHeight, 1};
    const SDL_GPUTextureTransferInfo destination = {transfer, 0, 0, 0};
    SDL_DownloadFromGPUTexture(pass, &source, &destination);
    SDL_EndGPUCopyPass(pass);
    SDL_GPUFence *fence = SDL_SubmitGPUCommandBufferAndAcquireFence(commands);
    if (fence == nullptr) {
        error = SDL_GetError();
        SDL_WaitForGPUIdle(m_gpuDevice);
        SDL_ReleaseGPUTransferBuffer(m_gpuDevice, transfer);
        return false;
    }
    const bool complete = SDL_WaitForGPUFences(m_gpuDevice, true, &fence, 1);
    SDL_ReleaseGPUFence(m_gpuDevice, fence);
    if (!complete) {
        error = SDL_GetError();
        SDL_ReleaseGPUTransferBuffer(m_gpuDevice, transfer);
        return false;
    }
    const void *mapped = SDL_MapGPUTransferBuffer(m_gpuDevice, transfer, false);
    if (mapped != nullptr) {
        const auto *data = static_cast<const std::uint8_t *>(mapped);
        pixels.assign(data, data + bytes);
        SDL_UnmapGPUTransferBuffer(m_gpuDevice, transfer);
        if (bgra) {
            for (std::size_t offset = 0; offset < pixels.size(); offset += 4)
                std::swap(pixels[offset], pixels[offset + 2]);
        }
        width = m_sceneTextureWidth;
        height = m_sceneTextureHeight;
    } else {
        error = SDL_GetError();
    }
    SDL_ReleaseGPUTransferBuffer(m_gpuDevice, transfer);
    return mapped != nullptr;
}

const char *SdlGpuRenderer::lastError() const {
    return m_error.empty() ? SDL_GetError() : m_error.c_str();
}
