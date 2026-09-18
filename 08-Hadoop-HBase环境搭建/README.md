# 08 · Hadoop + HBase 伪分布式环境搭建

**角色**：独立完成 ｜ **时间**：2026-09 ｜ **类型**：大数据课程实训

## 问题
在 VMware 虚拟机（CentOS/RHEL）中从零搭建 Hadoop 3.3.6 + HBase 2.4.8 伪分布式环境，实现建表、写入、查询全功能。

## 方案
- JDK 8 + Hadoop 配置（core-site/hdfs-site/yarn-site）+ SSH 免密
- HBase 对接 HDFS 存储，ZooKeeper 仲裁
- 编写一键部署脚本（环境检查→安装→配置→启动七步自动化）

## 排错实战（核心技术点）
1. **Hadoop 3.x root 启动限制**：需显式声明 `HDFS_NAMENODE_USER` 等 5 个用户变量
2. **HBase 2.4.8 与 Hadoop 3.3.6 异步 WAL 不兼容**：`FanOutOneBlockAsyncDFSOutputHelper` 异常 → 切换 `hbase.wal.provider=filesystem`
3. **进程残留导致假重启**：stop 脚本杀不掉 HMaster → 按进程名强杀 + PID 验证
4. **跨系统脚本编码**：Windows 编辑的 .sh 含 CRLF → sed 转换后执行

## 结果
- 环境全链路验证通过：建表、put、scan 正常，6 个 Java 进程（NameNode/DataNode/HMaster/HRegionServer 等）全部在线
- 形成可复用的一键部署脚本与排错手册

## 技术栈
Hadoop · HBase · ZooKeeper · Linux Shell · VMware
