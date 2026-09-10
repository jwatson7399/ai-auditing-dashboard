# Auto-merge guard check

A throwaway file used once to confirm that .github/workflows/commentary-merge.yml
refuses a pull request carrying the commentary label that touches a path outside
inbox/commentary/. This file is such a path, so the workflow must refuse and
comment rather than merge.

The pull request that carried this file was closed and never merged.
