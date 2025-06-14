"""Utility functions for test management and analysis."""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter

from src.testing.validation_agent import ValidationReport


class TestAnalyzer:
    """Utilities for analyzing test results over time."""
    
    def __init__(self, results_dir: str = "test_results"):
        self.results_dir = Path(results_dir)
        
    def load_all_results(self, days_back: Optional[int] = None) -> List[Dict]:
        """Load all test results from the results directory."""
        results = []
        cutoff_date = None
        
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for file in self.results_dir.glob("*_*.json"):
            if "aggregate" in file.name:
                continue
                
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    
                # Parse timestamp from filename
                timestamp_str = file.stem.split('_')[-2] + '_' + file.stem.split('_')[-1]
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                
                if cutoff_date and timestamp < cutoff_date:
                    continue
                    
                data['file_timestamp'] = timestamp
                results.append(data)
            except Exception as e:
                print(f"Error loading {file}: {e}")
                
        return results
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics from all test results."""
        results = self.load_all_results()
        
        if not results:
            return {"error": "No results found"}
        
        total_tests = len(results)
        scenarios = set(r['scenario_id'] for r in results)
        
        # Calculate averages
        avg_overall = sum(r['overall_score'] for r in results) / total_tests
        avg_goal = sum(r['goal_achievement_score'] for r in results) / total_tests
        avg_efficiency = sum(r['efficiency_score'] for r in results) / total_tests
        avg_clarity = sum(r['clarity_score'] for r in results) / total_tests
        avg_satisfaction = sum(r['user_satisfaction_score'] for r in results) / total_tests
        
        # Count recommendations
        recommendations = Counter(r['recommendation'] for r in results)
        
        # Collect all pain points
        all_pain_points = []
        for r in results:
            if 'pain_points' in r and isinstance(r['pain_points'], list):
                all_pain_points.extend(r['pain_points'])
        
        pain_point_counts = Counter(all_pain_points).most_common(10)
        
        return {
            'total_tests': total_tests,
            'unique_scenarios': len(scenarios),
            'average_scores': {
                'overall': round(avg_overall, 2),
                'goal_achievement': round(avg_goal, 2),
                'efficiency': round(avg_efficiency, 2),
                'clarity': round(avg_clarity, 2),
                'satisfaction': round(avg_satisfaction, 2)
            },
            'recommendations': dict(recommendations),
            'top_pain_points': pain_point_counts
        }
    
    def create_trend_report(self, output_file: str = "trend_analysis.html"):
        """Create an HTML report showing trends over time."""
        results = self.load_all_results()
        
        if not results:
            print("No results found to analyze")
            return
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(results)
        df['timestamp'] = pd.to_datetime(df['file_timestamp'])
        df = df.sort_values('timestamp')
        
        # Create visualizations
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Overall scores over time
        ax1 = axes[0, 0]
        scenarios = df['scenario_id'].unique()
        for scenario in scenarios:
            scenario_data = df[df['scenario_id'] == scenario]
            ax1.plot(scenario_data['timestamp'], scenario_data['overall_score'], 
                    marker='o', label=scenario, alpha=0.7)
        ax1.set_title('Overall Scores Over Time')
        ax1.set_ylabel('Score')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. Average scores by metric
        ax2 = axes[0, 1]
        metrics = ['goal_achievement_score', 'efficiency_score', 'clarity_score', 'user_satisfaction_score']
        metric_avgs = df.groupby('timestamp')[metrics].mean()
        for metric in metrics:
            ax2.plot(metric_avgs.index, metric_avgs[metric], 
                    marker='o', label=metric.replace('_', ' ').title())
        ax2.set_title('Average Metric Scores Over Time')
        ax2.set_ylabel('Score')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Success rate over time
        ax3 = axes[1, 0]
        df['success'] = df['recommendation'] == 'pass'
        success_rate = df.groupby('timestamp')['success'].mean() * 100
        ax3.plot(success_rate.index, success_rate.values, 
                marker='o', color='green', linewidth=2)
        ax3.set_title('Test Success Rate Over Time')
        ax3.set_ylabel('Success Rate (%)')
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3)
        
        # 4. Issue frequency
        ax4 = axes[1, 1]
        df['issue_count'] = df['pain_points'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        issue_trend = df.groupby('timestamp')['issue_count'].mean()
        ax4.plot(issue_trend.index, issue_trend.values, 
                marker='o', color='red', linewidth=2)
        ax4.set_title('Average Issues Per Test Over Time')
        ax4.set_ylabel('Number of Issues')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save the plot
        plot_file = self.results_dir / 'trend_analysis.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        # Generate HTML report
        html_content = self._generate_html_report(df, str(plot_file))
        
        with open(output_file, 'w') as f:
            f.write(html_content)
            
        print(f"Trend report saved to: {output_file}")
        
    def _generate_html_report(self, df: pd.DataFrame, plot_path: str) -> str:
        """Generate HTML content for the trend report."""
        
        # Calculate summary statistics
        latest_date = df['timestamp'].max()
        total_tests = len(df)
        unique_scenarios = df['scenario_id'].nunique()
        avg_score = df['overall_score'].mean()
        success_rate = (df['recommendation'] == 'pass').mean() * 100
        
        # Find most problematic scenarios
        problem_scenarios = df.groupby('scenario_id')['overall_score'].mean().sort_values().head(3)
        
        # Common pain points
        all_pain_points = []
        for points in df['pain_points']:
            if isinstance(points, list):
                all_pain_points.extend(points)
        
        from collections import Counter
        pain_point_counts = Counter(all_pain_points).most_common(5)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Trend Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .metric-label {{ color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .good {{ color: green; }}
        .bad {{ color: red; }}
        .warning {{ color: orange; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>Test Trend Analysis Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>Summary Statistics</h2>
        <div class="metric">
            <div class="metric-value">{total_tests}</div>
            <div class="metric-label">Total Tests Run</div>
        </div>
        <div class="metric">
            <div class="metric-value">{unique_scenarios}</div>
            <div class="metric-label">Unique Scenarios</div>
        </div>
        <div class="metric">
            <div class="metric-value">{avg_score:.2f}</div>
            <div class="metric-label">Average Score</div>
        </div>
        <div class="metric">
            <div class="metric-value">{success_rate:.1f}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
    </div>
    
    <h2>Trend Visualizations</h2>
    <img src="{plot_path}" alt="Trend Analysis Charts">
    
    <h2>Scenarios Needing Attention</h2>
    <table>
        <tr>
            <th>Scenario</th>
            <th>Average Score</th>
            <th>Status</th>
        </tr>
"""
        
        for scenario, score in problem_scenarios.items():
            status_class = 'bad' if score < 0.6 else 'warning'
            status = 'Needs Improvement' if score < 0.6 else 'Monitor'
            html += f"""
        <tr>
            <td>{scenario}</td>
            <td>{score:.2f}</td>
            <td class="{status_class}">{status}</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>Most Common Issues</h2>
    <table>
        <tr>
            <th>Issue</th>
            <th>Frequency</th>
        </tr>
"""
        
        for issue, count in pain_point_counts:
            html += f"""
        <tr>
            <td>{issue}</td>
            <td>{count}</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>Recommendations</h2>
    <ul>
"""
        
        # Generate recommendations based on data
        if avg_score < 0.7:
            html += "<li><strong>Overall performance needs improvement.</strong> Focus on the scenarios with lowest scores.</li>"
        
        if success_rate < 60:
            html += "<li><strong>Low success rate detected.</strong> Review common failure patterns across tests.</li>"
        
        if len(pain_point_counts) > 0 and pain_point_counts[0][1] > total_tests * 0.5:
            html += f"<li><strong>Critical issue found:</strong> '{pain_point_counts[0][0]}' affects over 50% of tests.</li>"
        
        # Check for improving/declining trends
        if len(df) > 5:
            recent = df.tail(5)['overall_score'].mean()
            older = df.head(5)['overall_score'].mean()
            if recent > older + 0.1:
                html += "<li class='good'><strong>Positive trend!</strong> Recent scores show improvement.</li>"
            elif recent < older - 0.1:
                html += "<li class='bad'><strong>Declining performance.</strong> Recent scores are lower than earlier tests.</li>"
        
        html += """
    </ul>
</body>
</html>
"""
        
        return html
    
    def compare_test_runs(self, run1_timestamp: str, run2_timestamp: str) -> Dict:
        """Compare two test runs to see improvements or regressions."""
        results = self.load_all_results()
        
        run1 = None
        run2 = None
        
        for result in results:
            timestamp = result['file_timestamp'].strftime('%Y%m%d_%H%M%S')
            if run1_timestamp in timestamp:
                run1 = result
            elif run2_timestamp in timestamp:
                run2 = result
                
        if not run1 or not run2:
            raise ValueError("Could not find both test runs")
            
        comparison = {
            'run1_timestamp': run1_timestamp,
            'run2_timestamp': run2_timestamp,
            'scenario': run1['scenario_id'],
            'score_change': run2['overall_score'] - run1['overall_score'],
            'metrics': {
                'goal_achievement': run2['goal_achievement_score'] - run1['goal_achievement_score'],
                'efficiency': run2['efficiency_score'] - run1['efficiency_score'],
                'clarity': run2['clarity_score'] - run1['clarity_score'],
                'satisfaction': run2['user_satisfaction_score'] - run1['user_satisfaction_score']
            },
            'issues_change': len(run2.get('pain_points', [])) - len(run1.get('pain_points', [])),
            'recommendation_change': f"{run1['recommendation']} → {run2['recommendation']}"
        }
        
        return comparison
    
    def generate_test_summary_csv(self, output_file: str = "test_summary.csv"):
        """Export all test results to CSV for external analysis."""
        results = self.load_all_results()
        
        if not results:
            print("No results found")
            return
            
        # Flatten the data for CSV
        flattened = []
        for result in results:
            row = {
                'timestamp': result['file_timestamp'],
                'scenario_id': result['scenario_id'],
                'overall_score': result['overall_score'],
                'goal_achieved': result['goal_achieved'],
                'goal_achievement_score': result['goal_achievement_score'],
                'efficiency_score': result['efficiency_score'],
                'clarity_score': result['clarity_score'],
                'user_satisfaction_score': result['user_satisfaction_score'],
                'total_turns': result['total_turns'],
                'recommendation': result['recommendation'],
                'pain_points_count': len(result.get('pain_points', [])),
                'bot_errors_count': len(result.get('bot_errors', [])),
                'immediate_fixes_count': len(result.get('immediate_fixes', []))
            }
            flattened.append(row)
            
        df = pd.DataFrame(flattened)
        df.to_csv(output_file, index=False)
        print(f"Test summary exported to: {output_file}")
        

def cleanup_old_results(days_to_keep: int = 30, results_dir: str = "test_results"):
    """Clean up test results older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    results_path = Path(results_dir)
    
    removed_count = 0
    for file in results_path.glob("*.json"):
        try:
            # Extract timestamp from filename
            parts = file.stem.split('_')
            if len(parts) >= 2:
                timestamp_str = parts[-2] + '_' + parts[-1]
                file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                
                if file_date < cutoff_date:
                    file.unlink()
                    removed_count += 1
        except Exception as e:
            print(f"Error processing {file}: {e}")
            
    print(f"Removed {removed_count} old test result files")


def run_regression_tests(baseline_dir: str, current_dir: str = "test_results") -> Dict:
    """Compare current test results against a baseline."""
    analyzer = TestAnalyzer(current_dir)
    baseline_analyzer = TestAnalyzer(baseline_dir)
    
    current_results = analyzer.load_all_results()
    baseline_results = baseline_analyzer.load_all_results()
    
    # Group by scenario
    current_by_scenario = {}
    baseline_by_scenario = {}
    
    for result in current_results:
        scenario = result['scenario_id']
        if scenario not in current_by_scenario:
            current_by_scenario[scenario] = []
        current_by_scenario[scenario].append(result)
        
    for result in baseline_results:
        scenario = result['scenario_id']
        if scenario not in baseline_by_scenario:
            baseline_by_scenario[scenario] = []
        baseline_by_scenario[scenario].append(result)
    
    regression_report = {
        'timestamp': datetime.now().isoformat(),
        'scenarios': {},
        'summary': {
            'passed': 0,
            'failed': 0,
            'improved': 0,
            'regressed': 0
        }
    }
    
    for scenario in set(current_by_scenario.keys()) | set(baseline_by_scenario.keys()):
        if scenario not in current_by_scenario:
            regression_report['scenarios'][scenario] = {'status': 'missing_in_current'}
            continue
        if scenario not in baseline_by_scenario:
            regression_report['scenarios'][scenario] = {'status': 'new_scenario'}
            continue
            
        # Compare average scores
        current_avg = sum(r['overall_score'] for r in current_by_scenario[scenario]) / len(current_by_scenario[scenario])
        baseline_avg = sum(r['overall_score'] for r in baseline_by_scenario[scenario]) / len(baseline_by_scenario[scenario])
        
        score_diff = current_avg - baseline_avg
        
        regression_report['scenarios'][scenario] = {
            'baseline_score': baseline_avg,
            'current_score': current_avg,
            'score_change': score_diff,
            'status': 'passed' if score_diff >= -0.05 else 'regressed'
        }
        
        if score_diff >= -0.05:
            regression_report['summary']['passed'] += 1
        else:
            regression_report['summary']['failed'] += 1
            
        if score_diff > 0.05:
            regression_report['summary']['improved'] += 1
        elif score_diff < -0.05:
            regression_report['summary']['regressed'] += 1
    
    return regression_report


# Convenience functions
def quick_analysis():
    """Run a quick analysis of recent test results."""
    analyzer = TestAnalyzer()
    
    print("Generating trend report...")
    analyzer.create_trend_report()
    
    print("Exporting test summary...")
    analyzer.generate_test_summary_csv()
    
    print("\nAnalysis complete! Check:")
    print("  - trend_analysis.html for visual trends")
    print("  - test_summary.csv for raw data")


if __name__ == "__main__":
    quick_analysis() 