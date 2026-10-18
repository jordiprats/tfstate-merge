# Merging resources from several terraform states

If you have several Terraform projects handling the deployment of different parts of an application and you want to consolidate them into a single project, you can either create a new Terraform state and import all the resources using `terraform import`, or you can use **tfstate-merge** to copy resources into the new state and consolidate it.

Let's assume we have some resources on the **infrastructure** project and some others on the **application** project, and we want to copy their state into the **infrastructure\_and\_application** project folder. We can merge the resources as follows:

```
$ python mergestates.py /home/user/terraform/infrastructure /home/user/terraform/application /home/user/terraform/infrastructure_and_application
Acquiring state lock. This may take a few moments...
Releasing state lock. This may take a few moments...
```

This tool pulls the Terraform state (`terraform state pull`) from all projects, then merges the resources from the source projects into the target project. If any resource is **duplicated**, the merge will fail:

```
$ python mergestates.py /home/user/terraform/infrastructure /home/user/terraform/application /home/user/terraform/infrastructure_and_application
Error reading source state "/tmp/tmpfdp7nj_p/merged": 3 problems:

- Duplicate resource instance in state: Instance data.aws_security_group.public_access appears multiple times in the state file.
Error pushing terraform state to /home/user/terraform/infrastructure_and_application
```

You will have to manually resolve the situation. **Data sources are allowed to be duplicated**, so the tool silently discards data sources from the source project if they already exist in the target.

---

## Usage

Merge resources from any number of source projects into a single target project:

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

## Requirements

- Python 3.x
- Terraform installed and available in the system PATH (any version from 0.12 to latest 1.x)
- Terraform workspaces must be initialised (`terraform init`) and have remote state configured

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
- **Conservative duplicate removal**: The script removes data resources from the source list by comparing full JSON objects. If the source and target dictionaries differ (e.g. different `instances` or `schema_version`), the removal fails and a **warning is printed to stderr**. The user must resolve the duplicate manually to be able to use `terraform state push`.
- **Serial increment is always +1**: The script always increments `serial` by 1, even if the target state already has a higher serial from concurrent changes. This could cause conflicts if multiple merges happen simultaneously.
- **No conflict resolution**: If a managed resource already exists in the target state with the same type/name, it will be duplicated. Terraform may later error when trying to apply the merged state.
- **Error handling**: Errors during `terraform state pull` or `terraform state push` cause the script to exit. The temporary directory is cleaned up only on success (unless `DRYRUN` is set).

## License

[MIT](LICENSE)
