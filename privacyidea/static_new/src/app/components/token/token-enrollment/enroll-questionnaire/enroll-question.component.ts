import { Component, Input, WritableSignal } from '@angular/core';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';

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
  configQuestions = [
    // TODO get this from system endpoint
    'What is your favorite color?',
    'What is your favorite animal?',
    'What is your favorite food?',
    'What is your favorite movie?',
    'What is your favorite book?',
    'What is your favorite song?',
    'What is your favorite sport?',
  ];
  configMinNumberOfAnswers = 3;

  text = TokenComponent.tokenTypes.find((type) => type.key === 'question')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() answers!: WritableSignal<Record<string, string>>;

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
      !currentAnswers[question] && answeredCount < this.configMinNumberOfAnswers
    );
  }
}
