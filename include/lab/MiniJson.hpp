#pragma once

#include "Lifetime.hpp"

#include <array>
#include <cctype>
#include <cstdlib>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace lab {

// A small, strict-enough JSON reader (RFC 8259 subset: no duplicate-key
// policy, \uXXXX escapes are decoded to UTF-8). Used only for the repository's
// own catalog files; it never evaluates anything.
struct Json {
    enum class Type { Null, Bool, Number, String, Array, Object };
    Type type = Type::Null;
    bool boolean = false;
    double number = 0.0;
    std::string string;
    std::vector<Json> array;
    std::string key;           // set on the members of an object
    std::vector<Json> object;  // members, each carrying its key

    const Json *get(const std::string &name) const EMU_LIFETIMEBOUND {
        for (const auto &member : object)
            if (member.key == name)
                return &member;
        return nullptr;
    }
    bool is_string() const { return type == Type::String; }
    bool is_array() const { return type == Type::Array; }
    bool is_object() const { return type == Type::Object; }
};

class JsonParser {
  public:
    explicit JsonParser(const std::string &text EMU_LIFETIMEBOUND) : text_(text) {}

    std::optional<Json> parse() {
        skip_space();
        std::optional<Json> value = parse_value(0);
        skip_space();
        if (!value || pos_ != text_.size()) {
            value.reset();
            return value;
        }
        return value;
    }

  private:
    static constexpr int kMaxDepth = 64;
    const std::string &text_;
    std::size_t pos_ = 0;

    void skip_space() {
        while (pos_ < text_.size() &&
               std::isspace(static_cast<unsigned char>(text_[pos_])))
            ++pos_;
    }
    bool consume(char c) {
        if (pos_ < text_.size() && text_[pos_] == c) {
            ++pos_;
            return true;
        }
        return false;
    }
    bool consume_word(const char *word) {
        const std::string w = word;
        if (text_.compare(pos_, w.size(), w) == 0) {
            pos_ += w.size();
            return true;
        }
        return false;
    }

    std::optional<Json> parse_value(int depth) {
        if (depth > kMaxDepth || pos_ >= text_.size())
            return std::nullopt;
        const char c = text_[pos_];
        Json value;
        if (c == '{')
            return parse_object(depth);
        if (c == '[')
            return parse_array(depth);
        if (c == '"') {
            auto s = parse_string();
            if (!s)
                return std::nullopt;
            value.type = Json::Type::String;
            value.string = *s;
            return value;
        }
        if (consume_word("true")) {
            value.type = Json::Type::Bool;
            value.boolean = true;
            return value;
        }
        if (consume_word("false")) {
            value.type = Json::Type::Bool;
            return value;
        }
        if (consume_word("null"))
            return value;
        return parse_number();
    }

    std::optional<Json> parse_number() {
        const char *start = text_.c_str() + pos_;
        char *end = nullptr;
        const double parsed = std::strtod(start, &end);
        if (end == start)
            return std::nullopt;
        pos_ += static_cast<std::size_t>(end - start);
        Json value;
        value.type = Json::Type::Number;
        value.number = parsed;
        return value;
    }

    static void append_utf8(std::string &out, unsigned code) {
        if (code < 0x80) {
            out.push_back(static_cast<char>(code));
        } else if (code < 0x800) {
            const std::array<char, 2> buf = {
                static_cast<char>(0xC0 | (code >> 6)),
                static_cast<char>(0x80 | (code & 0x3F))
            };
            out.append(buf.data(), buf.size());
        } else {
            const std::array<char, 3> buf = {
                static_cast<char>(0xE0 | (code >> 12)),
                static_cast<char>(0x80 | ((code >> 6) & 0x3F)),
                static_cast<char>(0x80 | (code & 0x3F))
            };
            out.append(buf.data(), buf.size());
        }
    }

    std::optional<std::string> parse_string() {
        if (!consume('"'))
            return std::nullopt;
        std::string out;
        while (pos_ < text_.size()) {
            const char c = text_[pos_++];
            if (c == '"')
                return out;
            if (c != '\\') {
                out += c;
                continue;
            }
            if (pos_ >= text_.size())
                return std::nullopt;
            const char e = text_[pos_++];
            switch (e) {
            case '"': out += '"'; break;
            case '\\': out += '\\'; break;
            case '/': out += '/'; break;
            case 'b': out += '\b'; break;
            case 'f': out += '\f'; break;
            case 'n': out += '\n'; break;
            case 'r': out += '\r'; break;
            case 't': out += '\t'; break;
            case 'u': {
                if (pos_ + 4 > text_.size())
                    return std::nullopt;
                const std::string hex = text_.substr(pos_, 4);
                char *end = nullptr;
                const unsigned long code = std::strtoul(hex.c_str(), &end, 16);
                if (end != hex.c_str() + 4)
                    return std::nullopt;
                pos_ += 4;
                append_utf8(out, static_cast<unsigned>(code));
                break;
            }
            default: return std::nullopt;
            }
        }
        return std::nullopt; // unterminated
    }

    std::optional<Json> parse_array(int depth) {
        consume('[');
        Json value;
        value.type = Json::Type::Array;
        skip_space();
        if (consume(']'))
            return value;
        while (true) {
            skip_space();
            auto item = parse_value(depth + 1);
            if (!item)
                return std::nullopt;
            value.array.push_back(std::move(*item));
            skip_space();
            if (consume(']'))
                return value;
            if (!consume(','))
                return std::nullopt;
        }
    }

    std::optional<Json> parse_object(int depth) {
        consume('{');
        Json value;
        value.type = Json::Type::Object;
        skip_space();
        if (consume('}'))
            return value;
        while (true) {
            skip_space();
            auto key = parse_string();
            if (!key)
                return std::nullopt;
            skip_space();
            if (!consume(':'))
                return std::nullopt;
            skip_space();
            auto item = parse_value(depth + 1);
            if (!item)
                return std::nullopt;
            item->key = std::move(*key);
            value.object.push_back(std::move(*item));
            skip_space();
            if (consume('}'))
                return value;
            if (!consume(','))
                return std::nullopt;
        }
    }
};

inline std::optional<Json> parse_json(const std::string &text) {
    return JsonParser(text).parse();
}

} // namespace lab
