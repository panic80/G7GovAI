// AccessBridge Types

export type WizardStep = 'mode' | 'input' | 'processing' | 'gaps' | 'output';

export const WIZARD_STEPS: WizardStep[] = ['mode', 'input', 'processing', 'gaps', 'output'];

export type OutputTab = 'form' | 'email' | 'meeting' | 'filled';

// Output mode selection (user can select multiple)
export type OutputMode = 'form' | 'email' | 'meeting';
