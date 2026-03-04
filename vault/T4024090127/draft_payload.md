<github_payload>
Hey everyone,

Hope you're having a productive week! I've put together a quick fix to address a subtle but important repository hygiene issue raised in the discussions. This patch introduces a `.gitignore` rule to proactively prevent `.bak` (backup) files from being tracked and committed in the future. This builds directly on the cleanup efforts from issue #537 by tackling the root cause of how those files ended up in the repo to begin with.

This change ensures that common editor backup files, which can inadvertently get committed, are now properly ignored, keeping our repository clean and focused on essential source code.

---

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -XX,XX +XX,XX @@
 # Example existing content:
 # Build artifacts
 /target/
 /build/

+# Editor backup files
+*.bak
```

*Note: The `@@ -XX,XX +XX,XX @@` line in the diff will vary based on the current line count of your `.gitignore` file. This diff assumes appending the new lines to the end of the file. If an "Editor backup files" section already exists, it should be placed there instead.*

---

**INVOICE:**

Please send bounty payment to my Rabby wallet: `0xFb39098275D224965a938f5cCAB512BbF737bdc7`
</github_payload>