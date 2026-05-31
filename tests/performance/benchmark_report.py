"""
性能基准测试报告生成器
生成美观的 HTML 和 Markdown 格式报告
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .benchmark_core import BenchmarkResult
from .benchmark_api import APIBenchmarkResult


class PerformanceReportGenerator:
    """性能报告生成器"""
    
    def __init__(self, output_dir: str = "benchmark_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def generate_markdown_report(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None,
        title: str = "OpsV-Kits 性能基准测试报告"
    ) -> str:
        """生成 Markdown 格式的报告"""
        
        lines = [
            f"# {title}",
            "",
            f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 执行摘要",
            "",
            self._generate_executive_summary(core_results, api_results),
            "",
            "## 核心模块性能测试结果",
            "",
            self._generate_core_results_table(core_results),
            "",
            "## 性能瓶颈分析",
            "",
            self._generate_bottleneck_analysis(core_results, api_results),
            "",
            "## 优化建议",
            "",
            self._generate_optimization_recommendations(core_results, api_results),
            "",
            "## 详细测试结果",
            "",
            self._generate_detailed_core_results(core_results),
        ]
        
        if api_results:
            lines.extend([
                "",
                "## API 性能测试结果",
                "",
                self._generate_api_results_table(api_results),
            ])
        
        content = "\n".join(lines)
        report_path = self.output_dir / f"benchmark_report_{self.timestamp}.md"
        report_path.write_text(content, encoding="utf-8")
        
        return str(report_path)
    
    def generate_html_report(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None,
        title: str = "OpsV-Kits 性能基准测试报告"
    ) -> str:
        """生成 HTML 格式的报告"""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 30px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ color: #34495e; margin-top: 30px; margin-bottom: 15px; border-left: 4px solid #3498db; padding-left: 10px; }}
        h3 {{ color: #555; margin-top: 20px; margin-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; font-weight: 600; }}
        tr:hover {{ background: #f8f9fa; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; }}
        .badge-good {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; text-align: center; }}
        .summary-card h3 {{ color: white; margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; }}
        .summary-card .value {{ font-size: 32px; font-weight: bold; }}
        .recommendation {{ background: #f8f9fa; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
        .bottleneck {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
        .timestamp {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto; }}
        .progress-bar {{ height: 8px; background: #e9ecef; border-radius: 4px; margin-top: 5px; overflow: hidden; }}
        .progress-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s ease; }}
        .progress-slow {{ background: #dc3545; }}
        .progress-medium {{ background: #ffc107; }}
        .progress-fast {{ background: #28a745; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="timestamp">测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        
        <h2>执行摘要</h2>
        {self._generate_html_executive_summary(core_results, api_results)}
        
        <h2>核心模块性能测试结果</h2>
        {self._generate_html_core_results_table(core_results)}
        
        <h2>性能瓶颈分析</h2>
        {self._generate_html_bottleneck_analysis(core_results, api_results)}
        
        <h2>优化建议</h2>
        {self._generate_html_optimization_recommendations(core_results, api_results)}
        
        <h2>详细测试结果</h2>
        {self._generate_html_detailed_core_results(core_results)}
        
        {self._generate_html_api_results(api_results) if api_results else ''}
    </div>
</body>
</html>
"""
        
        report_path = self.output_dir / f"benchmark_report_{self.timestamp}.html"
        report_path.write_text(html_content, encoding="utf-8")
        
        return str(report_path)
    
    def generate_json_report(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None
    ) -> str:
        """生成 JSON 格式的报告"""
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "core_results": {
                name: {
                    "name": r.name,
                    "iterations": r.iterations,
                    "min_time": r.min_time,
                    "max_time": r.max_time,
                    "mean_time": r.mean_time,
                    "median_time": r.median_time,
                    "std_dev": r.std_dev,
                    "throughput": r.throughput,
                    "memory_usage": r.memory_usage,
                    "cpu_usage": r.cpu_usage
                }
                for name, r in core_results.items()
            }
        }
        
        if api_results:
            report_data["api_results"] = {
                name: {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "requests": r.requests,
                    "failures": r.failures,
                    "min_response_time": r.min_response_time,
                    "max_response_time": r.max_response_time,
                    "avg_response_time": r.avg_response_time,
                    "median_response_time": r.median_response_time,
                    "p95_response_time": r.p95_response_time,
                    "p99_response_time": r.p99_response_time,
                    "requests_per_second": r.requests_per_second
                }
                for name, r in api_results.items()
            }
        
        report_path = self.output_dir / f"benchmark_report_{self.timestamp}.json"
        report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")
        
        return str(report_path)
    
    def _generate_executive_summary(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None
    ) -> str:
        """生成执行摘要（Markdown）"""
        if not core_results:
            return "无测试结果"
        
        total_tests = len(core_results)
        avg_throughput = sum(r.throughput for r in core_results.values()) / total_tests
        
        # 找出最慢和最快的测试
        sorted_results = sorted(core_results.values(), key=lambda x: x.mean_time)
        fastest = sorted_results[0]
        slowest = sorted_results[-1]
        
        lines = [
            f"- **总测试项**: {total_tests}",
            f"- **平均吞吐量**: {avg_throughput:.2f} ops/s",
            f"- **最快模块**: {fastest.name} ({fastest.mean_time:.4f}s)",
            f"- **最慢模块**: {slowest.name} ({slowest.mean_time:.4f}s)",
        ]
        
        return "\n".join(lines)
    
    def _generate_html_executive_summary(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None
    ) -> str:
        """生成执行摘要（HTML）"""
        if not core_results:
            return "<p>无测试结果</p>"
        
        total_tests = len(core_results)
        avg_throughput = sum(r.throughput for r in core_results.values()) / total_tests
        
        sorted_results = sorted(core_results.values(), key=lambda x: x.mean_time)
        fastest = sorted_results[0]
        slowest = sorted_results[-1]
        
        return f"""
        <div class="summary-grid">
            <div class="summary-card">
                <h3>总测试项</h3>
                <div class="value">{total_tests}</div>
            </div>
            <div class="summary-card">
                <h3>平均吞吐量</h3>
                <div class="value">{avg_throughput:.1f} <span style="font-size: 14px;">ops/s</span></div>
            </div>
            <div class="summary-card">
                <h3>最快模块</h3>
                <div class="value">{fastest.mean_time*1000:.1f} <span style="font-size: 14px;">ms</span></div>
            </div>
            <div class="summary-card">
                <h3>最慢模块</h3>
                <div class="value">{slowest.mean_time*1000:.1f} <span style="font-size: 14px;">ms</span></div>
            </div>
        </div>
        """
    
    def _generate_core_results_table(self, core_results: Dict[str, BenchmarkResult]) -> str:
        """生成核心模块结果表格（Markdown）"""
        lines = [
            "| 测试项 | 迭代次数 | 最小时间 | 最大时间 | 平均时间 | 中位数时间 | 吞吐量 |",
            "|--------|----------|----------|----------|----------|------------|--------|",
        ]
        
        for name, result in sorted(core_results.items()):
            lines.append(
                f"| {name} | {result.iterations} | {result.min_time:.4f}s | {result.max_time:.4f}s | "
                f"{result.mean_time:.4f}s | {result.median_time:.4f}s | {result.throughput:.2f} ops/s |"
            )
        
        return "\n".join(lines)
    
    def _generate_html_core_results_table(self, core_results: Dict[str, BenchmarkResult]) -> str:
        """生成核心模块结果表格（HTML）"""
        rows = []
        for name, result in sorted(core_results.items(), key=lambda x: x[1].mean_time):
            # 根据平均时间确定进度条颜色
            if result.mean_time < 0.01:
                progress_class = "progress-fast"
            elif result.mean_time < 0.1:
                progress_class = "progress-medium"
            else:
                progress_class = "progress-slow"
            
            # 计算相对性能
            max_time = max(r.mean_time for r in core_results.values())
            progress = min(100, (result.mean_time / max_time) * 100)
            
            rows.append(f"""
                <tr>
                    <td><strong>{name}</strong></td>
                    <td>{result.iterations}</td>
                    <td>{result.min_time*1000:.2f}ms</td>
                    <td>{result.max_time*1000:.2f}ms</td>
                    <td>
                        <strong>{result.mean_time*1000:.2f}ms</strong>
                        <div class="progress-bar">
                            <div class="progress-fill {progress_class}" style="width: {progress}%"></div>
                        </div>
                    </td>
                    <td>{result.median_time*1000:.2f}ms</td>
                    <td>{result.throughput:.1f} ops/s</td>
                </tr>
            """)
        
        return f"""
            <table>
                <thead>
                    <tr>
                        <th>测试项</th>
                        <th>迭代次数</th>
                        <th>最小时间</th>
                        <th>最大时间</th>
                        <th>平均时间</th>
                        <th>中位数时间</th>
                        <th>吞吐量</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        """
    
    def _generate_bottleneck_analysis(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None
    ) -> str:
        """生成瓶颈分析（Markdown）"""
        if not core_results:
            return "无足够数据进行分析"
        
        # 找出平均时间超过0.1秒的测试
        slow_tests = [r for r in core_results.values() if r.mean_time > 0.1]
        slow_tests.sort(key=lambda x: x.mean_time, reverse=True)
        
        lines = []
        if slow_tests:
            lines.append("### 潜在性能瓶颈")
            for test in slow_tests[:5]:
                lines.append(f"- **{test.name}**: 平均 {test.mean_time:.4f}s (吞吐量: {test.throughput:.2f} ops/s)")
        else:
            lines.append("未发现明显的性能瓶颈")
        
        return "\n".join(lines)
    
    def _generate_html_bottleneck_analysis(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None
    ) -> str:
        """生成瓶颈分析（HTML）"""
        if not core_results:
            return "<p>无足够数据进行分析</p>"
        
        slow_tests = [r for r in core_results.values() if r.mean_time > 0.1]
        slow_tests.sort(key=lambda x: x.mean_time, reverse=True)
        
        if not slow_tests:
            return """
                <div class="recommendation" style="border-left-color: #28a745; background: #d4edda;">
                    <strong>✓ 优秀!</strong> 未发现明显的性能瓶颈
                </div>
            """
        
        bottlenecks = []
        for test in slow_tests[:5]:
            bottlenecks.append(f"""
                <div class="bottleneck">
                    <strong>⚠️ {test.name}</strong>
                    <br>平均时间: {test.mean_time*1000:.2f}ms | 吞吐量: {test.throughput:.1f} ops/s
                </div>
            """)
        
        return f"<h3>潜在性能瓶颈</h3>{''.join(bottlenecks)}"
    
    def _generate_optimization_recommendations(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None
    ) -> str:
        """生成优化建议（Markdown）"""
        recommendations = [
            "### 通用优化建议",
            "",
            "1. **缓存策略**: 为频繁访问的数据实现缓存机制",
            "2. **连接池**: 优化数据库和 SSH 连接池配置",
            "3. **异步处理**: 对于 I/O 密集型操作使用异步处理",
            "4. **数据分页**: 对于大数据集实现分页查询",
            "5. **代码分析**: 使用 cProfile 进行详细的代码性能分析",
        ]
        
        # 根据测试结果添加特定建议
        slow_tests = [r for r in core_results.values() if r.mean_time > 0.1]
        if slow_tests:
            recommendations.append("")
            recommendations.append("### 特定模块优化")
            for test in slow_tests[:3]:
                recommendations.append(f"- **{test.name}**: 考虑重构或使用更高效的算法")
        
        return "\n".join(recommendations)
    
    def _generate_html_optimization_recommendations(
        self,
        core_results: Dict[str, BenchmarkResult],
        api_results: Optional[Dict[str, APIBenchmarkResult]] = None
    ) -> str:
        """生成优化建议（HTML）"""
        recommendations = [
            """
            <div class="recommendation">
                <strong>缓存策略</strong>: 为频繁访问的数据实现缓存机制
            </div>
            """,
            """
            <div class="recommendation">
                <strong>连接池</strong>: 优化数据库和 SSH 连接池配置
            </div>
            """,
            """
            <div class="recommendation">
                <strong>异步处理</strong>: 对于 I/O 密集型操作使用异步处理
            </div>
            """,
            """
            <div class="recommendation">
                <strong>数据分页</strong>: 对于大数据集实现分页查询
            </div>
            """,
            """
            <div class="recommendation">
                <strong>代码分析</strong>: 使用 cProfile 进行详细的代码性能分析
            </div>
            """,
        ]
        
        return "".join(recommendations)
    
    def _generate_detailed_core_results(self, core_results: Dict[str, BenchmarkResult]) -> str:
        """生成详细结果（Markdown）"""
        lines = []
        for name, result in sorted(core_results.items()):
            lines.append(f"### {name}")
            lines.append("")
            lines.append(f"- 迭代次数: {result.iterations}")
            lines.append(f"- 最小时间: {result.min_time:.6f}s")
            lines.append(f"- 最大时间: {result.max_time:.6f}s")
            lines.append(f"- 平均时间: {result.mean_time:.6f}s")
            lines.append(f"- 中位数时间: {result.median_time:.6f}s")
            lines.append(f"- 标准差: {result.std_dev:.6f}s")
            lines.append(f"- 吞吐量: {result.throughput:.2f} ops/s")
            if result.memory_usage is not None:
                lines.append(f"- 内存使用: {result.memory_usage:.2f} MB")
            if result.cpu_usage is not None:
                lines.append(f"- CPU 使用: {result.cpu_usage:.2f}%")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_html_detailed_core_results(self, core_results: Dict[str, BenchmarkResult]) -> str:
        """生成详细结果（HTML）"""
        sections = []
        for name, result in sorted(core_results.items()):
            sections.append(f"""
                <h3>{name}</h3>
                <table>
                    <tr><td><strong>迭代次数</strong></td><td>{result.iterations}</td></tr>
                    <tr><td><strong>最小时间</strong></td><td>{result.min_time*1000:.4f}ms</td></tr>
                    <tr><td><strong>最大时间</strong></td><td>{result.max_time*1000:.4f}ms</td></tr>
                    <tr><td><strong>平均时间</strong></td><td>{result.mean_time*1000:.4f}ms</td></tr>
                    <tr><td><strong>中位数时间</strong></td><td>{result.median_time*1000:.4f}ms</td></tr>
                    <tr><td><strong>标准差</strong></td><td>{result.std_dev*1000:.4f}ms</td></tr>
                    <tr><td><strong>吞吐量</strong></td><td>{result.throughput:.2f} ops/s</td></tr>
                    {f'<tr><td><strong>内存使用</strong></td><td>{result.memory_usage:.2f} MB</td></tr>' if result.memory_usage else ''}
                    {f'<tr><td><strong>CPU 使用</strong></td><td>{result.cpu_usage:.2f}%</td></tr>' if result.cpu_usage else ''}
                </table>
            """)
        
        return "".join(sections)
    
    def _generate_api_results_table(self, api_results: Dict[str, APIBenchmarkResult]) -> str:
        """生成 API 结果表格（Markdown）"""
        lines = [
            "| 端点 | 方法 | 请求数 | 失败数 | 最小响应 | 最大响应 | 平均响应 | P95响应 | P99响应 | RPS |",
            "|------|------|--------|--------|----------|----------|----------|---------|---------|-----|",
        ]
        
        for name, result in api_results.items():
            lines.append(
                f"| {result.endpoint} | {result.method} | {result.requests} | {result.failures} | "
                f"{result.min_response_time:.4f}s | {result.max_response_time:.4f}s | {result.avg_response_time:.4f}s | "
                f"{result.p95_response_time:.4f}s | {result.p99_response_time:.4f}s | {result.requests_per_second:.2f} |"
            )
        
        return "\n".join(lines)
    
    def _generate_html_api_results(self, api_results: Optional[Dict[str, APIBenchmarkResult]] = None) -> str:
        """生成 API 结果（HTML）"""
        if not api_results:
            return ""
        
        rows = []
        for name, result in api_results.items():
            success_rate = ((result.requests - result.failures) / result.requests * 100) if result.requests > 0 else 0
            
            rows.append(f"""
                <tr>
                    <td><strong>{result.endpoint}</strong></td>
                    <td>{result.method}</td>
                    <td>{result.requests}</td>
                    <td><span class="badge {'badge-danger' if result.failures > 0 else 'badge-good'}">{result.failures}</span></td>
                    <td>{result.min_response_time*1000:.2f}ms</td>
                    <td>{result.max_response_time*1000:.2f}ms</td>
                    <td><strong>{result.avg_response_time*1000:.2f}ms</strong></td>
                    <td>{result.p95_response_time*1000:.2f}ms</td>
                    <td>{result.p99_response_time*1000:.2f}ms</td>
                    <td>{result.requests_per_second:.1f}</td>
                </tr>
            """)
        
        return f"""
            <h2>API 性能测试结果</h2>
            <table>
                <thead>
                    <tr>
                        <th>端点</th>
                        <th>方法</th>
                        <th>请求数</th>
                        <th>失败数</th>
                        <th>最小响应</th>
                        <th>最大响应</th>
                        <th>平均响应</th>
                        <th>P95响应</th>
                        <th>P99响应</th>
                        <th>RPS</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        """
