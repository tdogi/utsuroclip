# AGENTS.md

## Workflow

Follow the workflow below when making changes to this workspace.

### 1. Reverse Engineering

First, inspect the current workspace and understand the existing implementation.

* Read relevant source code, configuration, tests, and documentation.
* Understand the current architecture and behavior.
* Identify the parts related to the requested change.
* Do not start implementation until the existing implementation is sufficiently understood.

### 2. Requirements

Clarify what needs to be changed based on the user's request and the existing implementation.

Focus user questions only on requirements that are critical enough that making an incorrect assumption could significantly affect the result.

Critical requirements include:

* Requirements that conflict with or contradict the existing implementation.
* Requirements that may introduce breaking changes.
* Requirements that have a significant impact on UX but are not sufficiently clear.

For non-critical details, use reasonable engineering judgment and proceed without unnecessary user confirmation.

#### Requirement Review Cycle

After drafting or updating the requirements, perform an adversarial self-review.

During the review:

* Do not assume the current interpretation is correct.
* Check whether the requirements accurately reflect the user's request.
* Check whether the requirements conflict with the existing implementation.
* Check whether any breaking change may be introduced.
* Check whether any UX-impacting behavior remains unclear.
* Focus on issues that could materially affect the final implementation.

If clarification is required:

* Ask the user only about the critical unresolved points.
* A single clarification round may contain multiple questions.
* For each question, provide multiple reasonable options when possible.
* Clearly identify the recommended option.
* Explain why that option is recommended.

After receiving the user's answers:

1. Update the requirements.
2. Perform the adversarial self-review again.
3. If critical ambiguity remains, ask another clarification round.

Repeat this cycle until the requirements are sufficiently clear or a maximum of 3 clarification/review cycles has been completed.

If critical ambiguity still remains after 3 cycles:

* Select the option that is judged to be the most appropriate.
* Include that assumption in the finalized requirements.
* Clearly identify the unresolved point, chosen assumption, reasoning, and potential impact when presenting the requirements to the user.

#### Requirement Approval

After the requirements have been finalized:

1. Present the finalized requirements to the user in a clear and concise form.
2. Present a brief summary of the latest adversarial self-review.

   * State whether any critical issue was found.
   * Briefly list important issues that were identified and how they were resolved.
   * Mention any remaining assumptions, risks, or points the user should be aware of.
   * If no significant issue remains, explicitly state that no critical issue was found.
   * Keep this summary concise and do not include detailed internal reasoning or chain-of-thought.
3. Include any assumptions that were made by the agent.
4. Ask the user to explicitly confirm whether the finalized requirements are acceptable.
5. Do not proceed to Working Branch or Planning until the user approves the finalized requirements.

If the user requests changes:

* Update the requirements based on the feedback.
* Perform the adversarial self-review again.
* Present the revised requirements and a brief summary of the latest adversarial self-review for approval again.

Proceed to Working Branch only after explicit user approval.

### 3. Working Branch

After the requirements have been approved, determine the working branch before starting Planning.

* Inspect the current branch and existing branch names.
* Follow the repository's existing branch naming patterns when proposing or naming a working branch.
* If the current branch is the main production branch such as `main` or `master`:

  1. Determine an appropriate recommended working branch name based on the approved requirements and the repository's existing branch naming patterns.
  2. Present the recommended branch name to the user.
  3. Briefly explain why the proposed branch name is appropriate.
  4. Ask the user to explicitly confirm whether to create and use the recommended branch, or whether another branch name should be used.
  5. Do not create or switch to the new working branch until the user approves the branch name.
  6. After approval, create the approved working branch and switch to it.
  7. Proceed to Planning.

* If the current branch is not the main production branch:

  1. Evaluate whether the current branch is appropriate for the approved requirements.
  2. Present the evaluation and recommended action to the user.
  3. If creating a new branch is recommended, propose a concrete branch name consistent with the repository's existing naming patterns.
  4. Ask whether to continue on the current branch or switch/create another branch.
  5. Do not proceed to Planning until the user approves the branch to use.

Do not discard uncommitted changes or modify, delete, reset, or force-update existing branches unless the operation is permitted by the execution policy and any required approval review has succeeded.

### 4. Git Safety Rules

These rules apply to all Git operations, including implementation work and CI/CD-related operations.

* Never force-push or otherwise rewrite remote Git history.
* Never push directly to `main` or `master`.
* Do not delete an existing branch unless the operation is permitted by the execution policy and any required approval review has succeeded.
* Do not discard uncommitted user changes unless the operation is permitted by the execution policy and any required approval review has succeeded.
* Do not use destructive commands such as `git reset --hard`, `git clean -fd`, `git restore`, or equivalent commands unless the operation is permitted by the execution policy and any required approval review has succeeded.
* Commit and push only from the current approved working branch.
* Before committing or pushing, verify the current branch with `git branch --show-current`.
* If the current branch is `main` or `master`, do not commit or push. Follow the Working Branch rules above and obtain user confirmation for the working branch before creating or switching to it.
* Pulling or updating the local `main` or `master` branch after deployment is allowed only for synchronizing it with the remote repository. Do not create new implementation commits directly on the main production branch.
* If any Git operation would overwrite, discard, delete, reset, or force-update existing user work or local repository state, require the applicable approval review defined by the execution policy before performing it.
* An approval review must never be used to bypass operations that are explicitly forbidden by the execution policy.
* If an operation is forbidden by the execution policy, do not perform it and report the restriction when relevant.

### 5. Planning

Create a concrete implementation plan based on the approved requirements.

* Identify the files and components that need to change.
* Determine the implementation approach.
* Consider compatibility with the existing architecture.
* Define how the implementation will be verified.
* Identify whether browser-based or other user-visible verification is required.
* Ensure the plan addresses all approved requirements before starting implementation.

### 6. Implementation

Implement the planned changes and verify them continuously.

#### Implementation and Verification

* Follow the existing codebase conventions and architecture.
* Keep changes focused on the approved requirements.
* Refactor related code when necessary to implement the change cleanly.
* Add or update relevant tests when appropriate.

After making changes:

1. Run the relevant build.
2. Run the relevant tests.
3. If either the build or tests fail, diagnose the failure and modify the implementation.
4. Run the build and tests again.
5. Continue this process until both the relevant build and tests succeed.
6. If the change affects a web application or other user-visible interface, perform the applicable Web Application Verification before proceeding to the implementation self-review.

Do not proceed to the implementation self-review while the relevant build or tests are failing.

If required web application verification cannot be completed, follow the Web Application Verification rules below and clearly identify the verification limitation before proceeding.

If the same failure continues without meaningful progress for 5 consecutive attempts:

* Stop the implementation loop.
* Do not continue repeating the same unsuccessful fix.
* Report the unresolved failure, likely cause, impact, and recommended next action.

#### Web Application Verification

When the approved requirements affect a web application, user interface, navigation, interaction, or other browser-visible behavior, verify the actual application behavior in addition to running automated builds and tests.

Prefer verification in the following order when the relevant environment is available:

1. Local development environment.
2. Preview or staging environment.
3. Production deployment as the final post-deployment verification.

During verification:

* Limit verification to behavior related to the approved requirements and important existing behavior that may have been affected.
* Verify the actual user-visible behavior rather than relying only on source-code inspection.
* Check relevant rendering, navigation, interactions, non-persistent state changes, and error behavior when applicable.
* Do not treat successful page loading alone as sufficient verification when the requirements involve interactive behavior.
* Use test or non-sensitive data when input is required.
* Do not enter, expose, transmit, or commit secrets, credentials, API keys, personal information, or other sensitive data.
* Never modify production data, user accounts, permissions, configuration, or other persistent production state during verification.
* Never perform destructive or irreversible operations against production data, accounts, or systems during verification.
* Do not access unrelated pages, external services, administrative interfaces, or systems beyond what is necessary for verification.
* Never perform or trigger any real external side effect, including payments, email delivery, notification delivery, account creation, or state-changing external API operations.
* Read-only external API access may be used only when necessary for verification and when it does not create, modify, or delete external data or trigger any other external side effect.
* If verification would require an external side effect, do not perform it. Report that the behavior could not be verified without causing an external side effect.
* If verification requires authentication or access that is unavailable, do not attempt to bypass the restriction.
* If browser-based verification cannot be completed reliably, do not assume success. Clearly report what was verified, what could not be verified, and why.

The implementation may proceed to the adversarial implementation self-review when:

* the relevant build succeeds,
* the relevant automated tests succeed, and
* any required web application verification has either completed successfully or its limitations have been clearly identified and do not prevent a meaningful review of requirement compliance.

#### Adversarial Implementation Self-Review

Only after the relevant build and tests succeed, and any required verification has either succeeded or its limitations have been clearly identified, perform an adversarial self-review of the implementation.

The primary purpose of this review is to verify that the implementation correctly satisfies the approved requirements.

During the review:

* Do not assume the implementation is correct simply because the build and tests pass.
* Compare the implementation directly against the approved requirements.
* Check each important requirement individually.
* Identify any requirement that is missing, only partially implemented, or implemented differently from what was approved.
* Check whether the implementation introduces behavior that contradicts the approved requirements.
* Check whether existing behavior that should remain unchanged has been unintentionally affected.
* Consider the results and limitations of browser-based or other user-visible verification when applicable.
* Focus on requirement compliance rather than minor style issues, optional improvements, or unnecessary refactoring.
* Return PASS when the approved requirements are satisfied and no significant requirement-related issue remains.

Review the implementation against:

* the approved requirements
* the existing behavior that must remain compatible
* the relevant tests
* the web application verification results and limitations when applicable
* important user-visible behavior

If the review identifies a requirement-related issue:

1. Modify the implementation.
2. Run the relevant build and tests again until they succeed.
3. Repeat the applicable Web Application Verification when the changed behavior is user-visible.
4. Perform the adversarial implementation self-review again.

The sequence below counts as one implementation review cycle:

Implementation or fixes
→ successful build and tests
→ applicable web application verification or clearly identified verification limitations
→ adversarial implementation self-review

Repeat the implementation review cycle until the review passes, up to a maximum of 3 cycles.

If the adversarial implementation self-review still does not pass after 3 cycles:

* Stop further review cycles.
* Report which requirements remain unsatisfied.
* Explain the impact.
* Provide the recommended next action.

### 7. CI/CD

After Implementation and the implementation self-review are complete, report that the implementation is complete and ask the user whether to proceed with the CI/CD flow.

Proceed only with the operations requested by the user.

If the user gives an instruction that includes multiple stages, such as "deploy", execute the required preceding stages as part of the same flow unless the user explicitly says otherwise.

All Git operations performed as part of the CI/CD flow must follow the Git Safety Rules and the active execution policy.

#### Commit

If the user instructs to commit:

* Review the current changes.
* Inspect recent Git commit history and follow the repository's existing commit message style.
* Create an appropriate commit message based on the implemented requirements and existing commit conventions.
* Verify that the current branch is the approved working branch.
* Commit the relevant changes.

#### Push and CI

If the user instructs to push or run CI:

* Commit any required uncommitted changes first if the instruction clearly includes that step.
* Verify that the current branch is the approved working branch.
* Push the working branch to the remote repository.
* Create or update the pull request when necessary.
* Monitor the CI checks.
* If CI fails, inspect the failure and report the cause and recommended action.
* Do not proceed to deployment while CI is failing.

#### Deploy

If the user instructs to deploy, perform the full delivery flow as needed:

1. Review the current changes.
2. If necessary, commit them using a message consistent with the repository's existing Git history.
3. Verify that the current branch is the approved working branch.
4. Push the working branch.
5. Create or update the pull request.
6. Monitor CI and confirm that it succeeds.
7. Merge the pull request into the main branch.
8. Monitor the CD workflow and confirm that deployment succeeds.
9. Access the published application and perform the applicable Web Application Verification against the deployed version.
10. To the extent permitted by the Web Application Verification rules, confirm that the implemented changes are reflected and that the important affected behavior works as expected.
11. In the current workspace, switch to the main branch and update it to the latest remote state without discarding local changes.
12. Report the commit, CI result, merge result, CD result, published application verification result, verification limitations if any, and local main branch update result.

The production verification performed after deployment must follow the Web Application Verification rules.

Production verification must remain non-destructive and must never modify persistent production state or trigger a real external side effect.

If any required stage fails, stop before the dependent stage and report the failure and recommended next action.

Do not perform operations beyond the scope of the user's instruction unless they are required preceding steps for the requested operation.

Do not discard local changes when switching branches. If local changes prevent safely switching to the main branch, report the situation to the user instead of forcing the switch.

### 8. Completion

When the work is complete or further progress has been stopped by one of the limits above, report:

* What was changed.
* Important implementation decisions.
* Build results.
* Test results.
* Web application verification results when applicable.
* Whether the adversarial implementation self-review passed.
* Commit result when applicable.
* CI result when applicable.
* Pull request and merge result when applicable.
* CD and deployment result when applicable.
* Published application verification result when applicable.
* Local main branch update result when applicable.
* Any unresolved requirements or assumptions.
* Any unresolved implementation issues.
* Any verification that could not be completed and why.
* Remaining limitations, risks, or concerns.
* Recommended next actions when applicable.