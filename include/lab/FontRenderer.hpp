#pragma once

#include <SDL3/SDL.h>

#include <memory>
#include <string>

namespace lab {

class FontRenderer {
  public:
    explicit FontRenderer(const std::string &path);
    ~FontRenderer();
    FontRenderer(const FontRenderer &) = delete;
    FontRenderer &operator=(const FontRenderer &) = delete;

    bool ready() const;
    float measure(const std::string &text) const;
    void draw(SDL_Renderer *renderer, float x, float y, const std::string &text,
              SDL_Color color, float scale = 1.0f);

  private:
    struct Data;
    std::unique_ptr<Data> data_;
};

} // namespace lab
