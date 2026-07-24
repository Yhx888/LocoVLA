# 39 CMake 与工程结构

## 岗位任务

把“我电脑能编译”升级为任何同事都能复现的目标、依赖和测试图。CMake 不是编译器，它生成构建系统；真正编译代码的是 GCC/Clang/MSVC。

## 五个工程边界

- `include/` 只放公开接口。
- `src/` 放实现，调用方不依赖内部细节。
- `tests/` 通过公开接口验证行为。
- 优先用 `find_package(Eigen3)` 复用已安装的 Eigen；没有时由 CMake 下载固定版本和 SHA-256 的官方归档，仍不把 Eigen 源码复制进本仓库。
- `target_link_libraries` 把依赖绑定到具体 target，而不是污染全局。

## 检查点

```bash
cmake -S cpp -B build/cpp
cmake --build build/cpp --verbose
ctest --test-dir build/cpp --output-on-failure
```

预期看到 `control_test` 通过。已安装 Eigen 时，先确认 CMake 查找的是哪个前缀；未安装时，CMake 会下载并校验 Eigen 3.4.0。不要把 Eigen 源码复制进本仓库来绕过依赖管理。

故意错误：删除 `target_include_directories`，读懂编译器“找不到头文件”所暴露的接口路径边界。

作品集：构建日志、依赖图和一次失败根因记录。
