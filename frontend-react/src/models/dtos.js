import { WorkflowStatus } from './enums';

/**
 * @typedef {Object} BranchStatuses
 * @property {string} resume_branch - e.g., WorkflowStatus.PROCESSING
 * @property {string} interview_branch
 * @property {string} outreach_branch
 */

/**
 * @typedef {Object} WorkflowMetadataDTO
 * @property {string} thread_id
 * @property {string} created_at
 * @property {string} overall_status
 * @property {BranchStatuses} active_branches
 * @property {string|null} current_review_section
 * @property {string[]} completed_sections
 */

/**
 * @typedef {Object} ReviewTaskDTO
 * @property {string} task_id
 * @property {number} version
 * @property {string} task_type
 * @property {string} section
 * @property {string} status - from WorkflowStatus
 * @property {string} created_at
 * @property {Object|string} proposal
 * @property {Object|string} original
 * @property {string} optimization_notes
 * @property {ReviewTaskDTO[]} proposal_history
 */

/**
 * @typedef {Object} InterviewQuestionDTO
 * @property {string} category
 * @property {string} question
 * @property {string} answer
 */

/**
 * @typedef {Object} InterviewDeckDTO
 * @property {string} thread_id
 * @property {string} status
 * @property {InterviewQuestionDTO[]} questions
 */

/**
 * @typedef {Object} OutreachCardDTO
 * @property {string} type
 * @property {string} subject
 * @property {string} body
 */

/**
 * @typedef {Object} OutreachWorkspaceDTO
 * @property {string} thread_id
 * @property {string} status
 * @property {OutreachCardDTO[]} cold_emails
 * @property {OutreachCardDTO[]} referrals
 * @property {OutreachCardDTO[]} followups
 */
