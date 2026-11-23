#include "../include/sdl_gpu_renderer.h"
#include <SDL3/SDL.h>
#include <cstring>

// The existing instrument widgets rasterize to an RGBA software surface.
// The GPU owns presentation and composites that UI with the native 3D pass.
bool SdlGpuRenderer::setPanelBackground(SDL_Surface *surface) {
    if (!m_gpuDevice || !surface || surface->format != SDL_PIXELFORMAT_RGBA32) return false;
    const auto w = static_cast<Uint32>(surface->w), h = static_cast<Uint32>(surface->h);
    if (w != m_backgroundWidth || h != m_backgroundHeight) {
        const SDL_GPUTextureCreateInfo ti{SDL_GPU_TEXTURETYPE_2D,SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM,
            SDL_GPU_TEXTUREUSAGE_SAMPLER,w,h,1,1,SDL_GPU_SAMPLECOUNT_1,0};
        const SDL_GPUTransferBufferCreateInfo bi{SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD,w*h*4,0};
        auto *texture = SDL_CreateGPUTexture(m_gpuDevice,&ti);
        auto *buffer = SDL_CreateGPUTransferBuffer(m_gpuDevice,&bi);
        if (!texture || !buffer) {
            if (texture) SDL_ReleaseGPUTexture(m_gpuDevice,texture);
            if (buffer) SDL_ReleaseGPUTransferBuffer(m_gpuDevice,buffer);
            return false;
        }
        if (m_background) SDL_ReleaseGPUTexture(m_gpuDevice,m_background);
        if (m_backgroundTransfer) SDL_ReleaseGPUTransferBuffer(m_gpuDevice,m_backgroundTransfer);
        m_background = texture;
        m_backgroundTransfer = buffer;
        m_backgroundWidth = w;
        m_backgroundHeight = h;
    }
    auto *dst = static_cast<Uint8*>(SDL_MapGPUTransferBuffer(m_gpuDevice,m_backgroundTransfer,true));
    if (!dst) return false;
    auto *src = static_cast<const Uint8*>(surface->pixels);
    for (Uint32 y=0; y<h; ++y) std::memcpy(dst+y*w*4,src+y*surface->pitch,w*4);
    SDL_UnmapGPUTransferBuffer(m_gpuDevice,m_backgroundTransfer);
    auto *commands = SDL_AcquireGPUCommandBuffer(m_gpuDevice);
    if (!commands) return false;
    auto *copy = SDL_BeginGPUCopyPass(commands);
    if (!copy) { SDL_CancelGPUCommandBuffer(commands); return false; }
    const SDL_GPUTextureTransferInfo source{m_backgroundTransfer,0,w,h};
    const SDL_GPUTextureRegion dest{m_background,0,0,0,0,0,w,h,1};
    SDL_UploadToGPUTexture(copy,&source,&dest,true);
    SDL_EndGPUCopyPass(copy);
    return SDL_SubmitGPUCommandBuffer(commands);
}
