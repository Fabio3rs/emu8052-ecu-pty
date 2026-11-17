#pragma once

#ifdef __clang__
#define EMU_LIFETIMEBOUND [[clang::lifetimebound]]
#else
#define EMU_LIFETIMEBOUND
#endif
