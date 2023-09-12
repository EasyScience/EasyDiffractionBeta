This is a test version of EasyDiffraction with improved GUI and overall performance. This version temporarily does not use the EasyScience framework, contains only CrysPy as calculation engine and uses only Lmfit for minimization.  

### New Features

- Implemented loading of two-column data from `*.xy` files.
- Comments with `#` are now possible in data file headers.

### Bug Fixes

- `U_iso` are now automatically converted to `B_iso` (temporary fix) when loading a phase from CIF.
- Type symbols with oxidation state, e.g. `O2-`, are now partially supported.
