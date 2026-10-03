# Automated-test template (not active)

`tests.yml.example` is ready to place at `.github/workflows/tests.yml` when
workflow editing is authorised. It installs the tested top-level environment,
runs all model/dashboard tests and regenerates synthetic evidence on Python 3.11.
The workflow grants only `contents: read`; it has no deployment or secret access.

Current status: local tests pass; no remote Actions success is claimed. The
publishing credential lacks workflow modification scope. Do not broaden token
permissions without the account owner's explicit approval.

启用时可在GitHub网页编辑器创建 `.github/workflows/tests.yml`，粘贴模板并提交。
需要账户重新登录且允许编辑工作流。也可以在明确授权后，为发布凭证补充相应
权限。模板本身不会运行，不影响当前项目和报告发布。
