import {
  Component,
  computed,
  EventEmitter,
  inject,
  OnInit,
  Output,
  Signal,
} from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  SystemService,
  SystemServiceInterface,
} from '../../../../services/system/system.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { QuestionApiPayloadMapper } from '../../../../mappers/token-api-payload/question-token-api-payload.mapper';
export interface QuestionEnrollmentOptions extends TokenEnrollmentData {
  type: 'question';
  answers: Record<string, string>;
}

@Component({
  selector: 'app-enroll-question',
  standalone: true,
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
export class EnrollQuestionComponent implements OnInit {
  protected readonly enrollmentMapper: QuestionApiPayloadMapper = inject(
    QuestionApiPayloadMapper,
  );
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly systemService: SystemServiceInterface =
    inject(SystemService);

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'question')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  // FormGroup dynamically filled with FormControls for each question
  questionForm = new FormGroup<Record<string, AbstractControl<string>>>({});
  // Stores the names of the question FormControls for the template
  questionControlNames: string[] = [];

  // Configured questions from the system
  readonly configQuestions = computed(() => {
    const cfg =
      this.systemService.systemConfigResource.value()?.result?.value || {};
    return Object.entries(cfg)
      .filter(([k]) => k.startsWith('question.question.'))
      .map(([k, v]) => ({
        question: k.replace('question.question.', ''),
        text: v,
      }));
  });

  readonly configMinNumberOfAnswers: Signal<number> = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return cfg && cfg['question.num_answers']
      ? parseInt(cfg['question.num_answers'], 10)
      : 0;
  });

  private answeredCount(): number {
    return Object.values(this.questionForm.controls).filter(
      (control) => control?.value && control.value.trim() !== '',
    ).length;
  }

  ngOnInit(): void {
    this.updateFormControls();
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  private updateFormControls(): void {
    // Remove existing controls
    Object.keys(this.questionForm.controls).forEach((key) => {
      this.questionForm.removeControl(key);
    });
    this.questionControlNames = [];

    const newControls: { [key: string]: FormControl<string | null> } = {};
    this.configQuestions().forEach((q) => {
      const controlName = `answer_${q.question.replace(/\s+/g, '_')}`;
      this.questionControlNames.push(controlName);
      const control = new FormControl<string | null>('', [Validators.required]);
      this.questionForm.addControl(controlName, control);
      newControls[controlName] = control;
    });
    this.aditionalFormFieldsChange.emit(newControls);
    // Validator for minimum number of answers
    this.questionForm.setValidators(() => {
      return this.answeredCount() >= this.configMinNumberOfAnswers()
        ? null
        : { minAnswers: true };
    });
    this.questionForm.updateValueAndValidity();
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      return of(null);
    }

    const answers: Record<string, string> = {};
    this.configQuestions().forEach((q) => {
      const controlName = `answer_${q.question.replace(/\s+/g, '_')}`;
      answers[q.question] = this.questionForm.get(controlName)?.value ?? '';
    });

    const enrollmentData: QuestionEnrollmentOptions = {
      ...basicOptions,
      type: 'question',
      answers: answers,
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
