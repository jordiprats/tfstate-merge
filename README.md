# tfstate-merge

Merge resources from multiple Terraform states into a single target state. Useful when you want to consolidate resources from different projects/workspaces into one state without re-importing them manually.

## Requirements

- Python 3.x
- Terraform installed and available in the system PATH (any version from 0.12 to latest 1.x)
- Terraform workspaces must be initialised (`terraform init`) and have remote state configured

## Usage

```bash
python mergestates.py <project1> <project2> ... <target_project>
```

Each argument is a **directory path** containing a Terraform workspace. The last argument is the **target** project where all resources will be merged. The preceding projects are **source** projects whose resources are merged into the target.

You can also merge a **single specific resource** from a source project by appending `:<resource_path>` to the directory argument:

```bash
python mergestates.py \
    /path/to/projectA \
    /path/to/projectB:module.foo.aws_instance.bar \
    /path/to/target
```

The resource path follows Terraform's address format:
- Managed resources: `<type>.<name>`
- Data resources: `data.<type>.<name>`
- Resources inside modules: `module.<module_name>.<type>.<name>`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG`  | `False` | Print verbose debug output during execution |
| `DRYRUN` | `False` | Simulate the merge without actually pushing the merged state to the target |

Set them to any truthy value (e.g. `export DEBUG=1`).

## How It Works

1. Pulls the current Terraform state from each source project using `terraform state pull`
2. Pulls the target project's state
3. Merges resources from source states into the target state:
   - **General merge** (no `:resource_path`): All resources from the source state are added. Data resources that already exist in the target are skipped.
   - **Specific resource merge** (with `:resource_path`): Only the matching resource is added (unless it already exists as a data resource in the target).
4. Increments the `serial` field to trigger a state version bump.
5. Pushes the merged state back to the target project using `terraform state push`.

## Terraform State Format Compatibility

The script works with Terraform state format **version 4** (used since Terraform 0.12). It relies on the `resources` array and `serial` field, which remain stable across Terraform 1.x releases.

`terraform state pull` and `terraform state push` are standard commands available in all Terraform versions since 0.12.

## Limitations & Caveats

- **Module path ignored in general merge**: When merging all resources from a source state, the `exists_resource` check only compares `mode`, `type`, and `name` – it does **not** consider the `module` key. Resources with the same type/name in different modules may be incorrectly treated as duplicates.
- **Fragile duplicate removal**: The script removes data resources from the source list by comparing full JSON objects (`resources.remove(resource)`). If the source and target dictionaries differ (e.g. different `instances` or `schema_version`), the removal silently fails and the resource is added as a duplicate.
- **Serial increment is always +1**: The script always increments `serial` by 1, even if the target state already has a higher serial from concurrent changes. This could cause conflicts if multiple merges happen simultaneously.
- **No conflict resolution**: If a managed resource already exists in the target state with the same type/name, it will be duplicated. Terraform may later error when trying to apply the merged state.
- **Error handling**: Errors during `terraform state pull` or `terraform state push` cause the script to exit. The temporary directory is cleaned up only on success (unless `DRYRUN` is set).

## Example

Merge states from `project-alpha` and `project-beta` into `project-gamma`:

```bash
python mergestates.py /home/user/project-alpha /home/user/project-beta /home/user/project-gamma
```

Merge a single resource `aws_instance.web` from `project-alpha` into `project-gamma`:

```bash
python mergestates.py /home/user/project-alpha:aws_instance.web /home/user/project-gamma
```

## License

[MIT](LICENSE)
