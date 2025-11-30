# Changelog

All notable changes to Spec Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (No unreleased changes)

### Changed
- (No unreleased changes)

## [1.1.0] - 2025-11-29

### Added

#### Beads Integration Scripts
- **create-beads-issues.sh**: Bulk create Beads issues from tasks.md (workaround for `bd create --file` segfault bug)
  - Intelligent priority detection (P1/P2/P3)
  - Auto-detection of labels (parallel, backend, frontend, testing, user stories)
  - 0.1s delay between creates to avoid overwhelming the system
  - Validation, error handling, and colored output
  - Saves mapping to `/tmp/beads-mapping.txt` for verification

- **update-tasks-with-beads-ids.sh**: Link Beads IDs back to tasks.md
  - Updates task format from `- [ ] T001 Description` to `- [ ] (speckit-abc.1) T001 Description`
  - Uses Python for JSON parsing and regex matching
  - Creates timestamped backup before modifications
  - Validates all changes with user-friendly output

#### Documentation Enhancements
- **Example 4 in README.md**: Complete Beads integration workflow
  - 7-step process from initialization through implementation
  - Shows how to create epic, bulk import tasks, link IDs, and drive implementation

- **Troubleshooting sections in README.md**:
  - Beads bulk import workaround instructions
  - Analyze phase warning guidance
  - Clear explanations of when and why to use each tool

### Changed

#### Templates
- **tasks-template.md**:
  - Added **IMPORTANT** reminder to run `/speckit.analyze` after generating tasks
  - Added comprehensive Beads Integration section with 4-step workflow
  - Clarified that Beads provides persistent memory across sessions

- **plan-template.md**:
  - Added **CRITICAL** warning about graceful degradation requirements
  - Emphasized need to define fallback strategies for:
    - External API failures (timeouts, retry policies, fallback data sources)
    - Service failures (degraded mode operation)
    - Data unavailability (cached/default responses)
  - Added note to verify fallback strategy tasks during `/speckit.analyze` phase

#### Slash Commands
- **speckit.tasks.md**:
  - Added reminder in report section to run `/speckit.analyze` after task generation
  - Emphasizes consistency validation before implementation

- **speckit-orchestrate.md**:
  - Added note that analyze phase is skipped in streamlined workflow
  - Recommends using `/speckit-workflow-v2` for full quality gates
  - Suggests running `/speckit.analyze` manually if consistency validation needed

- **speckit.implement.md**:
  - Added new step 2: "Verify consistency validation"
  - Recommends running `/speckit.analyze` before implementation begins
  - Explains why analyze matters: catches missing requirements, scope creep, graceful degradation gaps
  - Does not block implementation if user chooses to proceed without analyze
  - Renumbered subsequent steps accordingly

#### Documentation
- **README.md**:
  - Updated Example 1 to include `/speckit.analyze` step with emphasis
  - Updated directory structure to show new Beads integration scripts
  - Added descriptions of what each Beads script does

### Fixed
- Workaround for Beads `bd create --file` segfault bug (panic at markdown.go:338)
  - Root cause: bulk markdown import causes nil pointer dereference
  - Solution: Individual issue creation with rate limiting

## [1.0.0] - 2025-11-29

### Added
- Initial public release of Spec Kit workflow system
- Specification-driven development framework
- Integration with Claude Code slash commands
- Quality gates and validation at each workflow phase
- User story prioritization system
- Cross-artifact consistency analysis
- Dependency-ordered task generation
- Support for both git and non-git repositories

---

## Version History Format

### Types of Changes

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

### Version Numbers

- **MAJOR**: Breaking changes to workflow or command interfaces
- **MINOR**: New features, new commands, template enhancements
- **PATCH**: Bug fixes, documentation updates
