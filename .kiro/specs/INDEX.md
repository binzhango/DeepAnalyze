# DeepAnalyze Documentation Index

## 📚 Documentation Overview

This directory contains comprehensive documentation for understanding and extending the DeepAnalyze project.

---

## 🎯 Quick Start Guide

**New to DeepAnalyze?** Read in this order:

1. **SUMMARY.md** (15 min) - Quick overview of the entire system
2. **project-analysis.md** (45 min) - Comprehensive architecture analysis
3. **detailed-code-execution.md** (30 min) - Deep dive into code execution
4. **code-examples.md** (20 min) - Practical examples

**Ready to extend?** Continue with:

5. **data-sources-extension/requirements.md** (30 min) - Requirements for Azure Blob & PostgreSQL

---

## 📖 Document Descriptions

### deepanalyze-understanding/

#### 1. SUMMARY.md ⭐ **START HERE**
**Quick reference guide (15 min read)**

- What is DeepAnalyze?
- 3-server architecture diagram
- 5-step workflow
- Key components overview
- Special tags explanation
- Your extension goals
- Quick commands

**Best for:** Getting oriented quickly

---

#### 2. project-analysis.md 📘 **COMPREHENSIVE**
**Complete system documentation (45 min read)**

**Contents:**
- Executive summary
- Architecture overview with diagrams
- Core components deep dive:
  - DeepAnalyzeVLLM class
  - API Server (main, config, chat, file, models, storage, utils)
- Complete data flow diagrams
- Prompt template structure
- Training pipeline
- Demo interfaces (WebUI, CLI, JupyterUI)
- Evaluation benchmarks
- Key design patterns
- Extension points
- Dependencies
- Configuration summary
- Security considerations
- Performance characteristics
- Common use cases
- Troubleshooting guide

**Best for:** Understanding the entire system architecture

---

#### 3. detailed-code-execution.md 🔬 **TECHNICAL**
**In-depth code execution analysis (30 min read)**

**Contents:**
- Complete `generate()` method walkthrough
- 8-phase execution flow:
  1. Initialization
  2. Multi-round loop
  3. API call to vLLM
  4. Response processing
  5. Code detection
  6. Code execution
  7. Feedback loop
  8. Completion
- `execute_code()` implementation details
- Advanced execution (subprocess isolation)
- Environment configuration
- Timeout handling
- Async version
- Workspace management
- File tracking with WorkspaceTracker
- Complete 4-round example
- Security considerations
- Performance characteristics
- Debugging tips

**Best for:** Understanding how code generation and execution works

---

#### 4. code-examples.md 💻 **PRACTICAL**
**Hands-on code examples (20 min read)**

**Contents:**
- Example 1: Basic usage
- Example 2: Step-by-step execution trace (4 rounds)
  - Round 1: Data loading
  - Round 2: Data analysis
  - Round 3: Visualization
  - Round 4: Final answer
- Example 3: Error handling and recovery
- Example 4: `execute_code()` implementation
- Example 5: Advanced subprocess execution
- Example 6: Async execution
- Example 7: Complete API request flow

**Best for:** Learning through practical examples

---

#### 5. README.md 📋 **NAVIGATION**
**Documentation guide and roadmap**

**Contents:**
- Document descriptions
- Extension spec overview
- Quick reference
- Key concepts
- Implementation roadmap
- Key insights
- Extension strategy
- Security checklist
- Performance checklist
- Testing strategy
- Next steps
- Questions to consider
- Resources

**Best for:** Navigating the documentation and planning implementation

---

#### 6. training-process.md 🎓 **TRAINING DEEP DIVE**
**Complete training pipeline documentation (45 min read)**

**Contents:**
- 3-stage curriculum overview
- Stage 0: Vocabulary extension
- Stage 1: Single-ability fine-tuning (421K examples)
- Stage 2: Multi-ability cold start (26K examples)
- Stage 3: Reinforcement learning with GRPO
- Training data composition
- Hardware requirements
- Cost estimates
- How to reproduce training
- Fine-tuning for your domain
- Comparison with other approaches

**Best for:** Understanding how DeepAnalyze was trained and how to fine-tune it

---

#### 7. training-quick-reference.md ⚡ **TRAINING SUMMARY**
**Quick training reference (10 min read)**

**Contents:**
- 3-stage pipeline diagram
- Training data breakdown
- Configuration for each stage
- Cost estimates
- Quick start commands
- Fine-tuning guide
- Performance metrics
- Timeline summary

**Best for:** Quick reference for training and fine-tuning

---

### data-sources-extension/

#### requirements.md 📝 **SPECIFICATION**
**Requirements for Azure Blob Storage and PostgreSQL integration (30 min read)**

**Contents:**
- Introduction and glossary
- 10 comprehensive requirements:
  1. Azure Blob Storage Integration
  2. PostgreSQL Database Integration
  3. Data Source Management API
  4. Chat API Integration
  5. Code Execution Environment Enhancement
  6. Configuration and Security
  7. Error Handling and Logging
  8. Data Source Discovery and Metadata
  9. Data Source Templates and Examples
  10. Performance and Resource Management
- Each requirement includes:
  - User story
  - 5-7 acceptance criteria in EARS format

**Best for:** Understanding what needs to be built for data source support

---

## 🗺️ Reading Paths

### Path 1: Quick Understanding (30 min)
```
SUMMARY.md → code-examples.md (Examples 1-2)
```
**Goal:** Get basic understanding of how DeepAnalyze works

---

### Path 2: Developer Onboarding (2 hours)
```
SUMMARY.md → project-analysis.md → detailed-code-execution.md → code-examples.md
```
**Goal:** Comprehensive understanding for contributing to the project

---

### Path 3: Extension Development (3 hours)
```
SUMMARY.md → project-analysis.md (focus on Extension Points) → 
detailed-code-execution.md → data-sources-extension/requirements.md → README.md
```
**Goal:** Prepare to implement Azure Blob and PostgreSQL support

---

### Path 4: Architecture Review (1 hour)
```
project-analysis.md (Architecture, Components, Data Flow sections)
```
**Goal:** Understand system design for architecture decisions

---

### Path 5: Code Execution Deep Dive (1 hour)
```
detailed-code-execution.md → code-examples.md (Examples 2-6)
```
**Goal:** Master the code generation and execution pipeline

---

## 🎓 Key Concepts by Document

### Multi-Round Reasoning
- **SUMMARY.md**: Basic explanation with diagram
- **detailed-code-execution.md**: Complete walkthrough
- **code-examples.md**: Example 2 (4-round trace)

### Code Execution
- **SUMMARY.md**: High-level overview
- **project-analysis.md**: Component description
- **detailed-code-execution.md**: Implementation details
- **code-examples.md**: Examples 4-6

### Workspace Management
- **SUMMARY.md**: Basic concept
- **project-analysis.md**: Architecture section
- **detailed-code-execution.md**: WorkspaceTracker details
- **code-examples.md**: Example 2 (file tracking)

### API Integration
- **SUMMARY.md**: Quick commands
- **project-analysis.md**: API endpoints documentation
- **code-examples.md**: Example 7 (complete flow)

### Data Sources Extension
- **README.md**: Extension strategy
- **data-sources-extension/requirements.md**: Complete specification

---

## 📊 Document Statistics

| Document | Length | Reading Time | Complexity |
|----------|--------|--------------|------------|
| SUMMARY.md | ~500 lines | 15 min | ⭐ Easy |
| project-analysis.md | ~1000 lines | 45 min | ⭐⭐⭐ Advanced |
| detailed-code-execution.md | ~800 lines | 30 min | ⭐⭐⭐ Advanced |
| code-examples.md | ~700 lines | 20 min | ⭐⭐ Intermediate |
| README.md | ~400 lines | 20 min | ⭐⭐ Intermediate |
| requirements.md | ~300 lines | 30 min | ⭐⭐ Intermediate |

**Total:** ~3,700 lines, ~2.5 hours of reading

---

## 🔍 Find Information Quickly

### "How does code execution work?"
→ **detailed-code-execution.md** (Phase 6: Code Execution)

### "What are the API endpoints?"
→ **project-analysis.md** (Core Components → API Server)

### "How do I add a new data source?"
→ **README.md** (Extension Strategy) + **requirements.md**

### "What's the architecture?"
→ **SUMMARY.md** (Core Architecture) or **project-analysis.md** (Architecture Overview)

### "Show me a complete example"
→ **code-examples.md** (Example 2: Step-by-Step Execution Trace)

### "What are the security concerns?"
→ **project-analysis.md** (Security Considerations) + **detailed-code-execution.md** (Security Considerations)

### "How do I configure it?"
→ **project-analysis.md** (Configuration Summary)

### "What needs to be built for data sources?"
→ **data-sources-extension/requirements.md**

---

## 🛠️ Implementation Checklist

### Phase 1: Understanding ✅
- [x] Read SUMMARY.md
- [x] Read project-analysis.md
- [x] Read detailed-code-execution.md
- [x] Read code-examples.md
- [x] Understand architecture
- [x] Understand code execution

### Phase 2: Requirements ✅
- [x] Read requirements.md
- [x] Understand Azure Blob requirements
- [x] Understand PostgreSQL requirements
- [x] Understand API requirements
- [x] Understand security requirements

### Phase 3: Design ⏭️
- [ ] Design data source abstraction
- [ ] Design API endpoints
- [ ] Design credential management
- [ ] Design code execution integration
- [ ] Create sequence diagrams
- [ ] Define data models
- [ ] Review with stakeholders

### Phase 4: Implementation ⏭️
- [ ] Implement base classes
- [ ] Implement Azure Blob connector
- [ ] Implement PostgreSQL connector
- [ ] Implement API endpoints
- [ ] Implement credential encryption
- [ ] Update chat API
- [ ] Update code execution environment

### Phase 5: Testing ⏭️
- [ ] Unit tests
- [ ] Integration tests
- [ ] Security tests
- [ ] Performance tests
- [ ] End-to-end tests

### Phase 6: Documentation ⏭️
- [ ] API documentation
- [ ] Configuration guide
- [ ] Security guide
- [ ] Usage examples
- [ ] Troubleshooting guide

---

## 📞 Getting Help

### Understanding Issues
1. Check the relevant document from the index above
2. Look for examples in code-examples.md
3. Review the troubleshooting section in project-analysis.md

### Implementation Questions
1. Review the extension strategy in README.md
2. Check requirements.md for specifications
3. Look at existing code in the DeepAnalyze repository

### Architecture Decisions
1. Review project-analysis.md (Key Design Patterns)
2. Check README.md (Key Insights)
3. Consider security and performance checklists

---

## 🎯 Success Criteria

You'll know you understand DeepAnalyze when you can:

- [ ] Explain the 3-server architecture
- [ ] Describe the multi-round reasoning loop
- [ ] Trace a request from client to response
- [ ] Explain how code execution works
- [ ] Identify where to add new features
- [ ] Understand the security implications
- [ ] Design a new data source connector
- [ ] Implement API endpoints
- [ ] Write tests for new features

---

## 📚 Additional Resources

### In This Repository
- `README.md` - Main project README
- `API/README.md` - API documentation
- `deepanalyze.py` - Core inference engine
- `API/` - API server implementation

### External Resources
- [DeepAnalyze Paper](https://arxiv.org/abs/2510.16872)
- [DeepAnalyze Model](https://huggingface.co/RUC-DataLab/DeepAnalyze-8B)
- [Training Data](https://huggingface.co/datasets/RUC-DataLab/DataScience-Instruct-500K)
- [Project Homepage](https://ruc-deepanalyze.github.io/)

---

## 🔄 Document Updates

This documentation was created to support the Azure Blob Storage and PostgreSQL integration project.

**Last Updated:** 2024
**Version:** 1.0
**Status:** Complete - Ready for design phase

---

## 📝 Feedback

If you find any issues or have suggestions for improving this documentation:
1. Note the document name and section
2. Describe the issue or suggestion
3. Provide context about what you were trying to understand

---

**Happy Learning! 🚀**
