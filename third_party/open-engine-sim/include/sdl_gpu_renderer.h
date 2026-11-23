#ifndef ATG_ENGINE_SIM_SDL_GPU_RENDERER_H
#define ATG_ENGINE_SIM_SDL_GPU_RENDERER_H

#include "renderer.h"

#include <cstdint>
#include <string>
#include <vector>

struct SDL_GPUDevice;
struct SDL_GPUBuffer;
struct SDL_GPUTransferBuffer;
struct SDL_GPUGraphicsPipeline;
struct SDL_GPUTexture;
struct SDL_Surface;

class SdlGpuRenderer final : public Renderer {
public:
    SdlGpuRenderer();
    ~SdlGpuRenderer();

    bool initialize(void *nativeWindowHandle, const std::string &shaderDirectory, bool cadScene = false);
    bool installStaticGeometry(const std::vector<EngineSimVertex> &vertices,
                               const std::vector<std::uint16_t> &indices, std::string &error);
    void setClipPlane(const ysVector &plane, const ysVector &second = {}) { m_clipPlane = plane; m_secondPlane = second; }
    void setCadDeformation(const ysVector &parameters) { m_deformation = parameters; }
    bool supportsSectionCaps() const { return m_parityPipeline && m_capPipeline; }
    bool setPanelBackground(SDL_Surface *surface);
    void endSectionPart(std::size_t firstDraw, int quadVertex, int quadIndex, const ysMatrix &planeModel,
                        bool second = false);
    std::size_t drawCount() const { return m_submissions.size(); }
    void profileScene(std::uint64_t frameStart);
    void shutdown();
    void beginFrame(const ysVector &clearColor) override;
    // Coordinates use SDL GPU's top-left window convention. Scene submissions
    // are clipped to this rectangle; UI submissions continue over the window.
    void setSceneViewport(float x, float y, float width, float height) override;
    void uploadGeometry(
        const EngineSimVertex *vertices,
        int vertexCount,
        const std::uint16_t *indices,
        int indexCount) override;
    void submitGeometry(
        const EngineSimVertex *vertices,
        const std::uint16_t *indices,
        int baseVertex,
        int baseIndex,
        int faceCount,
        const ysMatrix &transform,
        const ysMatrix &cameraView,
        const ysMatrix &projection,
        const ysVector &color,
        std::uint32_t stage,
        int layer) override;
    void endFrame() override;
    bool captureSceneRgba(std::vector<std::uint8_t> &pixels,
                          std::uint32_t &width, std::uint32_t &height,
                          std::string &error);
    const char *lastError() const;
    bool failed() const { return !m_error.empty(); }

private:
    void *m_window;
    bool m_windowClaimed;
    SDL_GPUDevice *m_gpuDevice;
    SDL_GPUBuffer *m_vertexBuffer;
    SDL_GPUBuffer *m_indexBuffer;
    SDL_GPUTransferBuffer *m_vertexTransferBuffer;
    SDL_GPUTransferBuffer *m_indexTransferBuffer;
    SDL_GPUGraphicsPipeline *m_scenePipeline;
    SDL_GPUGraphicsPipeline *m_transparentPipeline = nullptr;
    SDL_GPUGraphicsPipeline *m_uiPipeline;
    SDL_GPUTexture *m_sceneTexture;
    SDL_GPUTexture *m_depthTexture;
    std::uint32_t m_sceneTextureWidth;
    std::uint32_t m_sceneTextureHeight;
    std::uint32_t m_depthTextureWidth;
    std::uint32_t m_depthTextureHeight;
    const EngineSimVertex *m_vertices;
    const std::uint16_t *m_indices;
    int m_vertexCount;
    int m_indexCount;
    ysVector m_clearColor;
    std::string m_error;
    float m_sceneViewportX;
    float m_sceneViewportY;
    float m_sceneViewportWidth;
    float m_sceneViewportHeight;
    SDL_GPUBuffer *m_staticVertices = nullptr;
    SDL_GPUBuffer *m_staticIndices = nullptr;
    bool m_cadScene = false;
    ysVector m_clipPlane{}, m_secondPlane{};
    ysVector m_deformation{};
    SDL_GPUGraphicsPipeline *m_parityPipeline = nullptr;
    SDL_GPUGraphicsPipeline *m_capPipeline = nullptr;
    std::uint32_t m_depthFormat = 0;
    SDL_GPUTexture *m_background = nullptr;
    SDL_GPUTransferBuffer *m_backgroundTransfer = nullptr;
    std::uint32_t m_backgroundWidth{}, m_backgroundHeight{};
    unsigned m_profileFrames = 0;
    double m_profileMs = 0;
    std::uint64_t m_profileStart{};

    struct Submission {
        int baseVertex;
        int baseIndex;
        int faceCount;
        ysMatrix transform;
        ysMatrix cameraView;
        ysMatrix projection;
        ysVector color;
        ysVector clipPlane, secondPlane;
        ysVector deformation;
        std::uint32_t stage;
        int layer;
    };
    std::vector<Submission> m_submissions;
    struct Section { std::size_t first, end; Submission plane; ysVector parityPlane; };
    std::vector<Section> m_sections;
};

#endif /* ATG_ENGINE_SIM_SDL_GPU_RENDERER_H */
