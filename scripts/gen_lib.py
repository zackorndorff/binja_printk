"""
Hack to generate a linkable library from the binaryninjacore.h header file
This makes up for the fact that we don't actually have it in CI.

We do this by parsing the header with the fantastic regex you see below. Then it
varies by platform.

On Windows we build a .def file that lists all found symbols as exports, then we
use Microsoft's lib.exe to make a .lib file we can link against.

On Mac and Linux, we build a .S assembly file that defines all found symbols
with just a ret after them, then we build that into a shared object or dynamic
library. On Mac we even build for x86_64 and M1 (turns out "ret" exists
everywhere :) )
"""

import argparse
import re
import os
import subprocess
import tempfile

from typing import List

COREFUNC_RE = re.compile(
    r"^\W*BINARYNINJACOREAPI\W+[A-Za-z0-9_ ]+\W+([A-Za-z0-9_]+)\([^;]*\);",
    re.MULTILINE,
)


def parse_header(header: str) -> List[str]:
    """Parse the binaryninjacore.h header into a list of function names

    Args:
        header: contents of header file

    Returns:
        List of function names
    """
    # Using a dictionary to ensure uniqueness
    found = {}
    for m in COREFUNC_RE.finditer(header):
        func_name = m.groups(1)[0]
        found[func_name] = True
    return list(found.keys())


def test_parse_header():
    teststr = """
        BINARYNINJACOREAPI bool BNAddTypeMemberTokens(BNType* type, BNBinaryView* data, BNInstructionTextToken** tokens, size_t* tokenCount,
        int64_t offset, char*** nameList, size_t* nameCount, size_t size, bool indirect);
        BINARYNINJACOREAPI asdf AZaz09(
        asdf);
        BINARYNINJACOREAPI int64_t BNWriteDatabaseSnapshotData(BNDatabase* database, int64_t* parents, size_t parentCount, BNBinaryView* file, const char* name, BNKeyValueStore* data, bool autoSave, void* ctxt, bool(*progress)(void*, size_t, size_t));
        BINARYNINJACOREAPI const char** BNSettingsGetStringList(BNSettings* settings, const char* key, BNBinaryView* view, BNSettingsScope* scope, size_t* inoutSize);
        BINARYNINJACOREAPI BNArchitecture* BNGetArchitectureForViewType(BNBinaryViewType* type, uint32_t id,
        BNEndianness endian);  // Deprecated, use BNRecognizePlatformForViewType

        """
    res = parse_header(teststr)
    assert len(res) == 5
    assert res[0] == "BNAddTypeMemberTokens"
    assert res[1] == "AZaz09"
    assert res[2] == "BNWriteDatabaseSnapshotData"
    assert res[3] == "BNSettingsGetStringList"
    assert res[4] == "BNGetArchitectureForViewType"


def generate_def(functions: List[str], dll_name: str) -> str:
    """Generate .def file defining provided functions

    Args:
        functions: list of functions to define
        dll_name: name for LIBRARY

    Returns:
        string containing a .def file that defines and exports those functions
    """
    text = []
    text.append("LIBRARY " + dll_name)
    text.append("")
    text.append("EXPORTS")
    for i in functions:
        text.append(" " * 4 + i)
    text.append("")
    return "\n".join(text)


def test_generate_def():
    functions = ["BNAddTypeMemberTokens", "AZaz09"]
    def_text = generate_def(functions, "binaryninjacore.dll")
    assert (
        def_text
        == """LIBRARY binaryninjacore.dll

EXPORTS
    BNAddTypeMemberTokens
    AZaz09
"""
    )


def generate_asm(functions: List[str], is_macos=False) -> str:
    """Generate .S file defining provided functions

    Args:
        symbols: list of functions to define

    Returns:
        string containing a .S file that defines and exports those functions
    """
    text = []
    if is_macos:
        text.append(".text")
        prefix = "_"
    else:
        text.append(".section .text")
        prefix = ""
    text.append("")
    for i in functions:
        sym_name = prefix + i
        text.append(".align 4")
        text.append(".global " + sym_name)
        text.append(sym_name + ":")
        text.append("\tret")
    text.append("")
    return "\n".join(text)


def test_generate_asm():
    functions = ["BNAddTypeMemberTokens", "AZaz09"]
    def_text = generate_asm(functions, is_macos=False)
    assert (
        def_text
        == """.section .text

.align 4
.global BNAddTypeMemberTokens
BNAddTypeMemberTokens:
	ret
.align 4
.global AZaz09
AZaz09:
	ret
"""
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate linkable library from binaryninjacore.h"
    )
    parser.add_argument(
        "-i",
        "--header",
        help="path to binaryninjacore.h",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--outfile",
        help="path to output file",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--platform",
        help="platform to build file for",
        required=True,
    )
    args = parser.parse_args()
    platform = args.platform.lower()

    # Parse binaryninjacore.h
    with open(args.header, "r") as fp:
        header_str = fp.read()
    functions = parse_header(header_str)

    # Generate source file contents to work with
    if platform == "windows":
        out_str = generate_def(functions, "binaryninjacore.dll")
        suffix = ".def"
    elif platform == "macos":
        out_str = generate_asm(functions, is_macos=True)
        suffix = ".S"
    elif platform == "linux":
        out_str = generate_asm(functions, is_macos=False)
        suffix = ".S"
    else:
        raise Exception(f"Unknown platform {args.platform}")

    # Now turn that source file into a linkable library
    hTmpfile, tmpfilename = tempfile.mkstemp(suffix=suffix)
    tempf = os.fdopen(hTmpfile, "w")
    try:
        try:
            tempf.write(out_str)
        finally:
            tempf.close()

        if platform == "windows":
            subprocess.run(
                ["lib", f"/DEF:{tmpfilename}", f"/OUT:{args.outfile}"],
                check=True,
            )
        elif platform == "macos":
            subprocess.run(
                [
                    "cc",
                    "-dynamiclib",
                    "-arch",
                    "arm64",
                    "-arch",
                    "x86_64",
                    f"-Wl,-install_name,{os.path.basename(args.outfile)}",
                    tmpfilename,
                    "-o",
                    args.outfile,
                ],
                check=True,
            )
        elif platform == "linux":
            subprocess.run(
                [
                    "cc",
                    tmpfilename,
                    "-fPIC",
                    "-shared",
                    f"-Wl,-soname,{os.path.basename(args.outfile)}",
                    "-o",
                    args.outfile,
                ],
                check=True,
            )
        else:
            raise Exception(f"Unknown platform {args.platform}")
    finally:
        os.unlink(tmpfilename)


if __name__ == "__main__":
    main()
