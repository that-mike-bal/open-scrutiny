/**
 * API client for RAG-based application generation
 */

import { getApiBase } from './api-config';

const API_BASE_URL = getApiBase();

export type QuestionCategory = 'entity_field' | 'selection_field' | 'substantive_field' | 'file_upload';

export interface RAGAnswerRequest {
  question_id: string;
  question_text: string;
  tld_string?: string;
  applicant_id?: string;
  application_id?: string;
  question_category?: QuestionCategory;
  user_prompt?: string;      // User-provided direction for generation
}

export interface RAGAnswerResponse {
  success: boolean;
  response: string;
  data_source: string;
  confidence: number;
  question_id: string;
  generated_at: string;
  tip?: string;              // Contextual hint for entity/selection fields
  question_category?: string;
  generation_status?: string; // insufficient_data, etc.
  error?: string;
}

export interface QuestionGuidanceResponse {
  success: boolean;
  response: string;
  data_source: string;
  confidence: number;
  question_id: string;
  generated_at: string;
  guidance_type: 'requirements' | 'template' | 'examples' | 'general';
}

export interface ApplicationGenerationRequest {
  application_id: string;
  question_ids?: string[];
  store_in_database?: boolean;
}

export interface ApplicationGenerationResponse {
  success: boolean;
  application_id: string;
  tld_string: string;
  total_questions: number;
  successful_answers: number;
  completion_percentage: number;
  results: RAGAnswerResponse[];
  generated_at: string;
  error?: string;
}

/**
 * Generate an answer for a specific ICANN application question using RAG
 */
export async function generateRAGAnswer(request: RAGAnswerRequest): Promise<RAGAnswerResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/applications/generate-answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error generating RAG answer:', error);
    return {
      success: false,
      response: `Error generating answer: ${error instanceof Error ? error.message : 'Unknown error'}`,
      data_source: 'error',
      confidence: 0,
      question_id: request.question_id,
      generated_at: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

/**
 * Get guidance and templates for a specific question
 */
export async function getQuestionGuidance(question_id: string, question_text: string): Promise<QuestionGuidanceResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/applications/question-guidance`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question_id,
        question_text
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      ...data,
      guidance_type: 'general' // Default type
    };
  } catch (error) {
    console.error('Error getting question guidance:', error);
    return {
      success: false,
      response: `Error getting guidance: ${error instanceof Error ? error.message : 'Unknown error'}`,
      data_source: 'error',
      confidence: 0,
      question_id,
      generated_at: new Date().toISOString(),
      guidance_type: 'general'
    };
  }
}

/**
 * Generate answers for multiple questions in an application
 */
export async function generateApplicationAnswers(request: ApplicationGenerationRequest): Promise<ApplicationGenerationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/applications/generate-multiple`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error generating application answers:', error);
    return {
      success: false,
      application_id: request.application_id,
      tld_string: '',
      total_questions: 0,
      successful_answers: 0,
      completion_percentage: 0,
      results: [],
      generated_at: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

/**
 * Copy text to clipboard with formatting optimized for ICANN tools
 */
export function copyToClipboard(text: string): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      // Clean the text for ICANN copy-paste
      const cleanText = text
        .replace(/📋.*?:\s*\n\n/, '') // Remove header
        .replace(/<!--.*?-->/g, '') // Remove HTML comments
        .replace(/\n{3,}/g, '\n\n') // Normalize line breaks
        .trim();

      navigator.clipboard.writeText(cleanText).then(
        () => resolve(true),
        () => resolve(false)
      );
    } catch (error) {
      console.error('Clipboard copy failed:', error);
      resolve(false);
    }
  });
}

/**
 * Format confidence score as percentage
 */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/**
 * Get data source display name and icon
 */
export function getDataSourceInfo(dataSource: string): { name: string; icon: string; color: string } {
  switch (dataSource) {
    case 'applicant_database':
    case 'applicant_data':
    case 'entity_data':
      return { name: 'Applicant Data', icon: '🏢', color: 'blue' };
    case 'ai_generated':
    case 'evaluation_synthesis':
    case 'tld_evaluation':
    case 'risk_analysis':
      return { name: 'AI Generated', icon: '🤖', color: 'purple' };
    case 'question_metadata':
      return { name: 'Question Options', icon: '📋', color: 'teal' };
    case 'question_guidance':
    case 'guidebook_section':
      return { name: 'ICANN Guidance', icon: '📚', color: 'green' };
    case 'file_upload':
      return { name: 'File Upload', icon: '📎', color: 'gray' };
    case 'insufficient_data':
      return { name: 'No Data', icon: '⚠️', color: 'amber' };
    default:
      return { name: 'Generated', icon: '✨', color: 'gray' };
  }
}