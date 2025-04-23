import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenService } from '../../../../services/token/token.service';
import { SystemService } from '../../../../services/system/system.service';

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
  configQuestions = signal<{ question: string; text: unknown }[]>([]);
  configMinNumberOfAnswers = signal(0);

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'question')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() answers!: WritableSignal<Record<string, string>>;

  constructor(
    private tokenService: TokenService,
    private systemService: SystemService,
  ) {
    this.systemService.getSystemConfig().subscribe((response) => {
      const config = response?.result?.value;
      if (
        config &&
        Object.keys(config).some((key) => key.startsWith('question.question.'))
      ) {
        const questions = Object.entries(config)
          .filter(([key]) => key.startsWith('question.question.'))
          .map(([key, value]) => ({
            question: key.replace('question.question.', ''),
            text: value,
          }));
        this.configQuestions.set(questions);

        if (config['question.num_answers']) {
          this.configMinNumberOfAnswers.set(
            parseInt(config['question.num_answers'], 10),
          );
        }
      }
    });
  }

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
