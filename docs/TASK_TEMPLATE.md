---
# 任务执行协议

## 1. 任务文件创建
1. 阅读用户输入的任务描述
2. 创建任务文件，按以下步骤执行：
  - 文件命名格式为 `YYYY-MM-DD_序号.md`，放置在项目根目录的 `.tasks` 目录中
  - 不要重复使用已存在的任务文件
3. 将任务模板的内容复制到任务文件中
4. 根据以下内容填写任务文件中的详细信息：
   a. 用户输入的任务描述
   b. 项目概述（特别注意相关文件的内容）
5. 仔细检查是否完全按照步骤2-4执行

## 2. 任务分析
1. 通过查看相关代码和功能来全面分析任务，按以下步骤执行：
  a. 找出解决任务所需的核心文件和功能
    - 将发现的内容记录在任务文件的"任务分析"部分
  b. 扩展分析
    - 分析当前"任务分析"中的内容
    - 查看与当前分析内容相关的文件和功能
    - 将新发现的细节添加到任务文件的"任务分析"部分
  c. 重复步骤b，直到完全理解任务涉及的所有内容
2. 整理任务文件中的"任务分析"部分
  - 这一步必须在完成步骤1之后进行
  - 以合理的方式组织"任务分析"部分的内容

## 3. 任务迭代
1. 检查任务文件中"任务进展"下的更新，确保不重复之前的错误
2. 根据需要修改代码
  - 对于每次修改，按以下步骤执行：
    1. 在任务文件的"任务进展"部分添加记录，使用以下模板：
      ```
      [时间]
      - 添加、修改或删除的内容
      - 涉及修改的函数和文件名称
      - 修改的必要性说明
      - 仍存在的问题
      ```
    2. 确认修改是否成功：
      - 在当前修改记录底部添加 `状态：成功/失败`
      - 如果修改失败，重新执行本步骤

## 4. 任务完成
1. 在确认所有修改都已完成后：
  - 检查任务文件的"任务进展"部分
  - 确保所有问题都已解决

## 5. 最终审查
1. 回顾所有完成的工作，填写任务文件中的"最终审查"部分

---

# 任务文件模板

## 基本信息
- 文件名: [任务文件名]
- 创建时间: [创建时间]
- 创建者: [创建者]

## 任务描述
[详细描述任务的目标、要求和预期结果]

## 项目概述
[项目背景信息，相关文件或功能的说明]

## 任务分析
[分析任务涉及的核心文件和功能]
- 核心文件：
  - [文件路径和主要功能]
- 相关功能：
  - [功能描述和实现方式]
- 潜在影响：
  - [可能影响到的其他部分]

## 当前执行步骤
[当前正在执行的步骤编号和描述]

## 任务进展
[记录任务的执行过程和状态]
- [时间]
  - 执行的操作：
  - 涉及的文件：
  - 修改原因：
  - 遇到的问题：
  - 状态：[成功/失败]

## 最终审查
[任务完成后的总结]
- 完成情况：
- 主要修改：
- 遗留问题：
- 后续建议：

---

# 占位符说明
- [任务文件名]: 任务文件的名称，格式为 YYYY-MM-DD_序号.md
- [创建时间]: 当前的日期和时间
- [创建者]: 当前用户的用户名

# 占位符获取命令
- [任务文件名]: `echo $(date +%Y-%m-%d)_$(($(find .tasks -maxdepth 1 -name "$(date +%Y-%m-%d)_*" | wc -l) + 1))`
- [创建时间]: `echo $(date +'%Y-%m-%d_%H:%M:%S')`
- [创建者]: `echo $(whoami)`