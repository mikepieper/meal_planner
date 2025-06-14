# CI/CD Integration Guide

This guide shows how to integrate the automated testing framework into your continuous integration and deployment pipelines.

## GitHub Actions Integration

### Basic Test Workflow

Create `.github/workflows/chatbot-tests.yml`:

```yaml
name: Chatbot Automated Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # Run tests daily at 2 AM UTC
    - cron: '0 2 * * *'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Set up environment
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
      run: |
        echo "Environment configured"
    
    - name: Run critical tests
      run: |
        python run_tests.py run --scenarios \
          busy_professional_weekly \
          parent_allergies_quick \
          diabetic_senior_daily
    
    - name: Generate test report
      if: always()
      run: |
        python -c "from src.testing.test_utilities import TestAnalyzer; TestAnalyzer().get_summary_stats()"
    
    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: test_results/
    
    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const summary = JSON.parse(fs.readFileSync('test_summary.json', 'utf8'));
          
          const comment = `## Chatbot Test Results
          
          **Overall Score**: ${summary.average_scores.overall}
          **Tests Passed**: ${summary.recommendations.pass || 0}/${summary.total_tests}
          
          <details>
          <summary>Detailed Scores</summary>
          
          - Goal Achievement: ${summary.average_scores.goal_achievement}
          - Efficiency: ${summary.average_scores.efficiency}
          - Clarity: ${summary.average_scores.clarity}
          - Satisfaction: ${summary.average_scores.satisfaction}
          
          </details>`;
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

### Regression Test Workflow

Create `.github/workflows/regression-tests.yml`:

```yaml
name: Regression Tests

on:
  push:
    branches: [ main ]

jobs:
  regression:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Download baseline results
      uses: actions/download-artifact@v3
      with:
        name: baseline-results
        path: baseline_results/
    
    - name: Run all tests
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        python run_tests.py run --all
    
    - name: Run regression analysis
      run: |
        python -c "
        from src.testing.test_utilities import run_regression_tests
        import json
        
        report = run_regression_tests('baseline_results', 'test_results')
        
        with open('regression_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Fail if any regressions
        if report['summary']['regressed'] > 0:
            print(f\"❌ {report['summary']['regressed']} scenarios regressed!\")
            exit(1)
        else:
            print(f\"✅ No regressions found!\")
        "
    
    - name: Update baseline if successful
      if: success()
      uses: actions/upload-artifact@v3
      with:
        name: baseline-results
        path: test_results/
```

## GitLab CI Integration

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - report

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

test:chatbot:
  stage: test
  image: python:3.11
  before_script:
    - pip install -r requirements.txt
  script:
    - python run_tests.py run --all
  artifacts:
    when: always
    paths:
      - test_results/
    reports:
      junit: test_results/junit.xml
  only:
    - merge_requests
    - main

generate:report:
  stage: report
  image: python:3.11
  dependencies:
    - test:chatbot
  script:
    - python -m src.testing.test_utilities
    - cp trend_analysis.html public/index.html
  artifacts:
    paths:
      - public
  only:
    - main
```

## Jenkins Pipeline

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
        LANGSMITH_API_KEY = credentials('langsmith-api-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'python -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }
        }
        
        stage('Run Tests') {
            parallel {
                stage('Critical Path Tests') {
                    steps {
                        sh '. venv/bin/activate && python run_tests.py run --scenarios busy_professional_weekly fitness_enthusiast_daily'
                    }
                }
                
                stage('Edge Case Tests') {
                    steps {
                        sh '. venv/bin/activate && python run_tests.py run --scenarios parent_allergies_quick diabetic_senior_daily'
                    }
                }
            }
        }
        
        stage('Analysis') {
            steps {
                sh '. venv/bin/activate && python -m src.testing.test_utilities'
                
                publishHTML(
                    target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'trend_analysis.html',
                        reportName: 'Chatbot Test Trends'
                    ]
                )
            }
        }
        
        stage('Quality Gate') {
            steps {
                script {
                    def results = readJSON file: 'test_summary.json'
                    def overallScore = results.average_scores.overall
                    
                    if (overallScore < 0.7) {
                        error("Quality gate failed: Overall score ${overallScore} is below threshold 0.7")
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'test_results/**/*', allowEmptyArchive: true
            
            emailext (
                subject: "Chatbot Tests: ${currentBuild.currentResult}",
                body: '''
                    Test Results:
                    - Build: ${BUILD_URL}
                    - Status: ${BUILD_STATUS}
                    - Test Report: ${BUILD_URL}Chatbot_Test_Trends
                ''',
                to: '${DEFAULT_RECIPIENTS}'
            )
        }
    }
}
```

## CircleCI Configuration

Create `.circleci/config.yml`:

```yaml
version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  test:
    executor: python/default
    steps:
      - checkout
      
      - python/install-packages:
          pkg-manager: pip
          
      - run:
          name: Run subset of tests
          command: |
            python run_tests.py run --scenarios \
              busy_professional_weekly \
              vegetarian_transition \
              student_budget_optimize
              
      - run:
          name: Generate analysis
          when: always
          command: |
            python -c "
            from src.testing.test_utilities import TestAnalyzer
            import json
            
            analyzer = TestAnalyzer()
            stats = analyzer.get_summary_stats()
            
            with open('summary.json', 'w') as f:
                json.dump(stats, f)
            "
            
      - store_artifacts:
          path: test_results
          destination: test-results
          
      - store_test_results:
          path: test_results

  nightly-full-test:
    executor: python/default
    steps:
      - checkout
      
      - python/install-packages:
          pkg-manager: pip
          
      - run:
          name: Run all tests
          command: python run_tests.py run --all
          no_output_timeout: 30m
          
      - run:
          name: Generate trend report
          command: python -m src.testing.test_utilities
          
      - store_artifacts:
          path: trend_analysis.html

workflows:
  test-on-commit:
    jobs:
      - test
      
  nightly:
    triggers:
      - schedule:
          cron: "0 0 * * *"
          filters:
            branches:
              only:
                - main
    jobs:
      - nightly-full-test
```

## Best Practices for CI/CD Integration

### 1. Test Selection Strategy

**Fast Feedback (PR/Commit)**
- Run 3-5 critical scenarios
- Focus on high-risk areas
- Target: < 5 minutes

**Comprehensive (Nightly/Release)**
- Run all test scenarios
- Generate trend reports
- Target: < 30 minutes

### 2. Environment Variables

Always required:
```bash
OPENAI_API_KEY=your-key
LANGSMITH_API_KEY=your-key  # Optional but recommended
```

Optional:
```bash
TEST_TIMEOUT=300  # Seconds per test
TEST_PARALLEL=true  # Run tests in parallel
TEST_OUTPUT_FORMAT=junit  # For CI integration
```

### 3. Failure Handling

```python
# Add to your CI scripts
import sys
from src.testing.test_utilities import TestAnalyzer

analyzer = TestAnalyzer()
stats = analyzer.get_summary_stats()

# Define quality gates
MIN_OVERALL_SCORE = 0.7
MAX_CRITICAL_ISSUES = 2

if stats['average_scores']['overall'] < MIN_OVERALL_SCORE:
    print(f"❌ Overall score {stats['average_scores']['overall']} below threshold {MIN_OVERALL_SCORE}")
    sys.exit(1)

critical_issues = sum(1 for issue, count in stats['top_pain_points'] if count > 5)
if critical_issues > MAX_CRITICAL_ISSUES:
    print(f"❌ Too many critical issues: {critical_issues}")
    sys.exit(1)

print("✅ All quality gates passed!")
```

### 4. Notifications

```python
# Slack notification example
import requests

def send_slack_notification(webhook_url: str, stats: dict):
    color = "good" if stats['average_scores']['overall'] > 0.7 else "danger"
    
    message = {
        "attachments": [{
            "color": color,
            "title": "Chatbot Test Results",
            "fields": [
                {"title": "Overall Score", "value": f"{stats['average_scores']['overall']:.2f}", "short": True},
                {"title": "Tests Run", "value": str(stats['total_tests']), "short": True},
                {"title": "Success Rate", "value": f"{stats['recommendations'].get('pass', 0) / stats['total_tests'] * 100:.1f}%", "short": True}
            ]
        }]
    }
    
    requests.post(webhook_url, json=message)
```

### 5. Performance Tracking

```yaml
# Add to your CI pipeline
- run:
    name: Track performance metrics
    command: |
      python -c "
      import time
      import json
      
      start = time.time()
      # Run your tests here
      duration = time.time() - start
      
      metrics = {
          'timestamp': time.time(),
          'duration': duration,
          'tests_per_second': num_tests / duration
      }
      
      with open('performance.json', 'w') as f:
          json.dump(metrics, f)
      "
```

## Monitoring and Alerts

### 1. Set Up Dashboards

Use your CI platform's dashboard features to track:
- Test success rate over time
- Average test scores
- Most common failures
- Test execution time

### 2. Alert Conditions

Configure alerts for:
- Overall score drops below 0.6
- Any scenario fails 3 times in a row
- New critical issues appear
- Test execution time increases >50%

### 3. Regular Reviews

Schedule weekly reviews of:
- Trend reports
- New issues discovered
- Performance metrics
- Test coverage gaps

## Troubleshooting CI Issues

### Common Problems

1. **API Rate Limits**
   - Add delays between tests
   - Use API key rotation
   - Cache test results

2. **Timeouts**
   - Increase timeout values
   - Run tests in parallel
   - Use smaller test subsets

3. **Flaky Tests**
   - Add retry logic
   - Improve test stability
   - Isolate problematic scenarios

4. **Resource Constraints**
   - Use larger CI runners
   - Optimize test efficiency
   - Clean up after tests

Remember: The goal is to catch issues early without slowing down development! 