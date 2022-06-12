#include <cinttypes>

#include "binaryninjaapi.h"
#include "mediumlevelilinstruction.h"

using namespace BinaryNinja;

extern "C" {
BN_DECLARE_CORE_ABI_VERSION;

static Ref<Symbol> sym = nullptr;
static std::mutex g_initialAnalysisMutex;

// Backwards map the KERN_* log level macros (or at least the second byte of
// them) We expect caller to pass us the byte after the SOH byte. Returns either
// a string or NULL if unknown.
const char* GetLogLevelFromByte(char logLevel) {
  switch (logLevel) {
    case '0':
      return "KERN_EMERG";
    case '1':
      return "KERN_ALERT";
    case '2':
      return "KERN_CRIT";
    case '3':
      return "KERN_ERR";
    case '4':
      return "KERN_WARNING";
    case '5':
      return "KERN_NOTICE";
    case '6':
      return "KERN_INFO";
    case '7':
      return "KERN_DEBUG";
    case 'c':
      return "KERN_CONT";
    default:
      return NULL;
  }
}

void PrintkFixerMLIL(Ref<AnalysisContext> analysisContext) {
  bool updated = false;
  Ref<MediumLevelILFunction> function =
      analysisContext->GetMediumLevelILFunction();
  Ref<BinaryView> bv = analysisContext->GetFunction()->GetView();

  // The scoped_lock allows us to lock all analysis threads to have only 1
  // thread search for the symbol reference to printk.
  {
    std::scoped_lock<std::mutex> lock(g_initialAnalysisMutex);
    if (!bv->HasInitialAnalysis()) {
      sym = bv->GetSymbolByRawName("printk");
      // Linux kernels after 5.15 use a printk indexing system which changed the
      // exported `printk` symbol into `_printk`.
      if (!sym) sym = bv->GetSymbolByRawName("_printk");
      if (!sym)
        LogWarn(
            "Failed to find printk: PrintkFixer won't do anything (is this a "
            "Linux kernel module?)");
    }
  }

  // Early return if the symbol could not be found.
  if (!sym) return;

  uint64_t printkAddr = sym->GetAddress();
  // LogDebug("Printk is at %zx", printkAddr);

  // Loop over each MLIL instruction in the function
  for (auto& i : function->GetBasicBlocks()) {
    for (size_t instrIndex = i->GetStart(); instrIndex < i->GetEnd();
         instrIndex++) {
      MediumLevelILInstruction insn = function->GetInstruction(instrIndex);
      if (insn.operation != MLIL_CALL) continue;

      // Get the address being called and see if it's printk
      auto dest = insn.GetDestExpr<MLIL_CALL>();
      auto destValue = dest.GetValue();
      // LogDebug("Checking if value is constant %zu %zu", (size_t)
      // destValue.value, (size_t) destValue.state);
      // Why is an ExternalPointerValue not constant?
      if (!(destValue.IsConstant() || destValue.state == ExternalPointerValue))
        continue;
      // LogDebug("Value was constant");
      if (printkAddr == (uint64_t)destValue.value) {
        // If it was printk let's look for a format string
        // If there are no arguments, bail, and if the format string address
        // isn't constant, bail.
        auto src = insn.GetParameterExprs<MLIL_CALL>();
        if (src.size() < 1) continue;
        auto fmtStr = src[0];
        auto fmtStrValue = fmtStr.GetValue();
        if (!fmtStrValue.IsConstant()) continue;
        auto val = fmtStrValue.value;

        // Read looking for the <SOH>[0-7] KERN_* macro
        // Somehow we can end up with multiple; in that case we skip to the end
        // for readability but comment the log level from the first one; I think
        // this only happens in the event of a coding error in the kernel module
        // under analysis
        const char SOH = 1;
        size_t offset = 0;
        uint64_t walkPtr = val;
        char logLevelByte = 0;
        char buf[2];
        // If you have more than 100 bytes of headers on your string, you're on
        // your own.
        while (offset < 100) {
          size_t readBytes = bv->Read(buf, walkPtr + offset, 2);
          if (readBytes != 2) break;
          if (buf[0] != SOH) break;

          offset += 2;
          if (!logLevelByte) {
            logLevelByte = buf[1];
          }
        }

        // If we never found a log level byte, something bad happened. Don't
        // patch.
        if (!logLevelByte) continue;

        // No need to patch if there wasn't a log level on the front
        if (offset == 0) continue;

        // We've met all our conditions; now we can go ahead and patch
        LogInfo("Patching MLIL call to printk at address 0x%" PRIx64
                " with fmtstr at 0x%" PRIx64,
                insn.address, val);

        // Actually patch the MLIL pointer value
        fmtStr.Replace(
            function->ConstPointer(fmtStr.size, val + offset, fmtStr));

        // Add a comment if there isn't already a comment at this address,
        // specifying the log level
        auto bnFunction = function->GetFunction();
        const auto cmtAddress = insn.address;
        auto oldCmt = bnFunction->GetCommentForAddress(cmtAddress);
        if (oldCmt.empty()) {
          const char* logLevelStr = GetLogLevelFromByte(logLevelByte);
          if (logLevelStr) {
            std::ostringstream cmt;
            cmt << "Log level: " << logLevelStr;
            bnFunction->SetCommentForAddress(cmtAddress, cmt.str());
          }
        }
        updated = true;
      }
    }
  }
  if (updated) {
    // Per Vector 35's example, if we modify the function, we need to tell the
    // core to regenerate SSA form
    function->GenerateSSAForm();
  }
}

BINARYNINJAPLUGIN bool CorePluginInit() {
  Ref<Workflow> myWorkflow = Workflow::Instance()->Clone("PrintkFixerWorkflow");
  myWorkflow->RegisterActivity(
      new Activity("extension.printkFixerMLIL", PrintkFixerMLIL));
  myWorkflow->Insert("core.function.analyzeTailCalls",
                     "extension.printkFixerMLIL");
  Workflow::RegisterWorkflow(myWorkflow,
                             R"#({
			"title": "Printk Fixer Workflow",
			"description": "Fixes display of printk strings in kernel modules by patching the format string pointer to point after the log level bytes",
			"capabilities": []
		})#");
  return true;
}
}
