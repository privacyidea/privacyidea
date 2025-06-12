import { Component, computed, Input, WritableSignal } from '@angular/core';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';
import { SystemService } from '../../../../services/system/system.service';

export interface QuestionEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'question';
  answers: Record<string, string>;
}

@Component({
  selector: 'app-enroll-question',
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatError,
  ],
  templateUrl: './enroll-question.component.html',
  styleUrl: './enroll-question.component.scss',
})
export class EnrollQuestionComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'question')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() answers!: WritableSignal<Record<string, string>>;

  configQuestions = computed(() => {
    const cfg =
      this.systemService.systemConfigResource.value()?.result?.value || {};
    return Object.entries(cfg)
      .filter(([k]) => k.startsWith('question.question.'))
      .map(([k, v]) => ({
        question: k.replace('question.question.', ''),
        text: v,
      }));
  });

  configMinNumberOfAnswers = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return cfg && cfg['question.num_answers']
      ? parseInt(cfg['question.num_answers'], 10)
      : 0;
  });

  constructor(
    private tokenService: TokenService,
    private systemService: SystemService,
  ) {}

  onAnswerChange(newValue: string, question: string): void {
    this.answers.update((currentAnswers) => ({
      ...currentAnswers,
      [question]: newValue,
    }));
  }

  isRequired(question: string): boolean {
    const currentAnswers = this.answers() || {};
    let answeredCount = Object.values(currentAnswers).filter(
      (answer) => answer && answer.trim() !== '',
    ).length;
    return (
      !currentAnswers[question] &&
      answeredCount < this.configMinNumberOfAnswers()
    );
  }
}
