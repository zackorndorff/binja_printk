# binja_printk

Quick Binary Ninja workflow to make Linux kernel modules easier to read.

I look for the `SOH, <DIGIT>` (or `0x01, 0x3N`, roughly) pattern at the start of
a string pointed to by a `printk` call, then I patch MLIL to increment the
pointer so that the string will display nicely. It's unpatched in LLIL and
patched in MLIL/HLIL.

There might be a better API for doing this, but I don't know what it is. Maybe
someone will tell me if I post this. Either way it was a fun way to play with
the Workflows API.

Note: I haven't seen any kernel CTF problems since I wrote this, so it's not
well tested :)

## Demo

```c
000002f0  uint64_t init_module()

000002f0      __fentry__()
00000316      uint32_t rax = __register_chrdev(0xcb, 0, 0x2000, 0x47c, 0x5c0)  {"cpu/cpuid"}
0000031d      uint32_t r12
0000031d      if (rax != 0)
0000032b          r12 = -0x10
00000331          printk(0x4b0, 0xcb)
```

Note the ugly printk invocation! We can do better!

```c
000002f0  uint64_t init_module()

000002f0      __fentry__()
00000316      uint32_t rax = __register_chrdev(0xcb, 0, 0x2000, 0x47c, 0x5c0)  {"cpu/cpuid"}
0000031d      uint32_t r12
0000031d      if (rax != 0)
0000032b          r12 = -0x10
00000331          printk("cpuid: unable to get major %d fo…", 0xcb)  // Log level: KERN_ERR
```

## Building

1. `git submodule update --init`
2. `mkdir build && cd build`
3. `cmake ..`
4. `make`
5. Move the generated `.so` / `.dylib` / `.dll` into your Binary Ninja plugin
   directory.

## Usage
1. Install it to your plugin directory. You just drop the binary there; you can
   click Tools > Open Plugin Folder in Binary Ninja to open it.

   If you trust my binaries, you can use the precompiled binaries found
   [on the release page](https://github.com/zackorndorff/binja_printk/releases).

   If you're on an Apple platform with Gatekeeper enabled, you'll need to remove
   the quarantine attribute on the dylib:
   `xattr -d com.apple.quarantine libbinja_printk.dylib`
2. Open With Options your `.ko`.
3. Scroll to the bottom section "Workflows". Enable them with the "Workflows
   Analysis Orchestration Framework" checkbox, then set "Function Workflow" to
   "PrintkFixerWorkflow". As the devs continue to improve workflows, presumably
   this will get more streamlined.
4. Click Open. Bask in the glory of readable strings.

## Requirements

* CMake
    * I don't know CMake, so excuse my poorly written build system please.
* A C++ compiler CMake can find
* Binary Ninja Commercial (it's required for Workflows at the moment)
    * Works on v3.1 stable
    * Last tested against v3.1.3632-dev

## Updating the binaryninja-api commits used for automated builds

Just update the submodule, it should be rebuilt automatically. The autobuild
will create a prerelease release. On tag, a draft release will be created that
can be manually approved.

So when a new Binary Ninja stable is released, the `vendor/api-stable` submodule
should be updated to point to whatever is current at that point.

When the dev ABI breaks and we get complaints when we try to load the plugin, we
should bump `vendor/api` to latest dev. Or whenever we need a new feature.

## Code formatting

`clang-format -style=Google main.cpp -i`

## License

This project copyright Zack Orndorff (@zackorndorff) and is available under the
MIT license. See [LICENSE](LICENSE).
