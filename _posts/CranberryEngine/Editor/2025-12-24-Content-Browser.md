---
title: "Editor Content Browser"
date: 2025-12-24
excerpt: "Notes on adding editor content browser. Archive notes"
mermaid: false
mathjax: false
categories: 
  - cranberry
sidebar:
  nav: "Cranberry"
---

## Creating Assets

The editor includes a Content Browser that streamlines asset creation. To create a new asset, follow these steps:

1. **Select a target folder** – Choose the directory where the asset should reside. The Content Browser provides easy access to this folder from any context or menu.
2. **Launch the asset wizard** – The wizard prompts you for a package name and automatically populates the necessary metadata.
3. **Create the package** – The editor helper routine generates the package in the chosen folder.
4. **Save immediately** – The new package is saved to disk right away.

Undo/redo support for asset creation is not yet implemented; it is planned for a future release. Keeping the initial implementation simple allowed us to focus on core functionality and stability.

## Deleting and Moving Assets

Both deletion and movement require updating all references that point to the affected assets.

### Deletion

1. Collect every package that will be removed, including those nested inside a folder slated for deletion.
2. Identify every referrer of those packages.
3. (Optional) Begin a transaction and move the assets to a temporary location.
4. Iterate through each referrer:
   - Add the referrer to the transaction.
   - Replace the deleted object's references with the user‑selected value (e.g., another asset or `null`). In the first implementation this defaults to `null`.
   - Record the modified fields in the transaction.
5. Execute the deletion routine for the targeted objects.
6. Fire the `onObjectModified` events for all objects that changed.

### Movement

Moving an asset is similar but involves copying it to a new location.

1. Gather the packages to be moved, recursing into sub‑folders if needed.
2. Find all referrers of the moving packages.
3. (Optional) Start a transaction and copy the assets to a temporary directory.
4. Copy the packages to the destination folder.
5. Refresh the asset registry so the new packages appear.
6. Process each referrer:
   - Add the referrer to the transaction.
   - Replace references pointing to the moved asset with the newly created package object.
   - Record edited fields.
7. Run the deletion routine on the original assets.
8. Emit `onObjectModified` events for all objects that changed.

Confirmation dialogs appear before any deletion or move operation to prevent accidental data loss.

## Copying Assets

Copying assets is handled by serializing them to a byte array, eliminating the need for custom reflector helpers. The workflow consists of two phases: preparation and execution.

### Preparation

1. Identify the root directory that contains the assets to be copied.
2. Enumerate all assets that require copying.

### Execution

1. Determine the destination root directory and store its path in the transaction.
2. Capture the engine path of the destination root.
3. Create an intermediate folder that mirrors the source structure for undo/redo purposes.
4. For each source asset:
   - Ensure the full parent directory hierarchy exists in both the intermediate and destination roots.
   - Determine the relative package path and check for name collisions; generate a unique name if necessary.
   - Serialize the source asset to a byte array.
   - Create a temporary package with the chosen name.
   - Deserialize the byte array into the new package.
   - Rename the root object to match the package name when required.
   - Serialize the new package and write it to the intermediate directory at the appropriate relative path.
   - Retrieve the engine package path and root object path from the destination location; store these details for later loading.
   - Apply the transaction, which loads the copied objects into the engine’s asset manager.

The earlier discussion about modifying the module reflector to generate copy helpers has been removed because the serialization approach is now sufficient and provides a more reliable and maintainable solution.
