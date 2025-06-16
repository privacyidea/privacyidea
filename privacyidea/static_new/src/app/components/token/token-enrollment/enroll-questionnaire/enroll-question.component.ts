import {
  Component,
  computed,
  EventEmitter,
  OnInit,
  Output,
} from '@angular/core';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { SystemService } from '../../../../services/system/system.service';

import { Observable } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
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
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'question')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: TokenEnrollmentData,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  // FormGroup that is dynamically filled with FormControls for each question
  questionForm = new FormGroup<Record<string, AbstractControl<string>>>({});
  // Stores the names of the question FormControls for the template
  questionControlNames: string[] = [];

  // Configured questions from the system
  // Continue to use `computed` to react to changes in the system configuration.
  // The FormControls are created/updated in `ngOnInit` and on changes to `configQuestions`.
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

  readonly configMinNumberOfAnswers = computed(() => {
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

  constructor(
    // private questionService: QuestionService,
    private tokenService: TokenService,
    private systemService: SystemService,
    private enrollmentMapper: QuestionApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.updateFormControls();
    this.clickEnrollChange.emit(this.onClickEnroll);

    // Observe changes to `configQuestions` to recreate FormControls if necessary.
    // This is important if the system configuration changes during the component's lifetime.
    // `effect` would be an option here, or a more explicit subscription if `computed` does not directly support `valueChanges`.
    // For this example, we assume that `configQuestions` is stable upon initialization
    // or the component is recreated if the configuration changes.
    // A more robust solution could use `effect` to call `updateFormControls`.
  }

  private updateFormControls(): void {
    // Remove existing controls
    Object.keys(this.questionForm.controls).forEach((key) => {
      this.questionForm.removeControl(key);
    });
    this.questionControlNames = [];

    const newControls: { [key: string]: FormControl<string | null> } = {};
    this.configQuestions().forEach((q) => {
      const controlName = `answer_${q.question.replace(/\s+/g, '_')}`; // Unique name for FormControl
      this.questionControlNames.push(controlName);
      const control = new FormControl<string | null>('', [Validators.required]); // Each answer is initially required
      this.questionForm.addControl(controlName, control);
      newControls[controlName] = control;
    });
    this.aditionalFormFieldsChange.emit(newControls);
    // Validator for minimum number of answers (optional, if validated server-side)
    this.questionForm.setValidators(() => {
      return this.answeredCount() >= this.configMinNumberOfAnswers()
        ? null
        : { minAnswers: true };
    });
    this.questionForm.updateValueAndValidity();
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      return undefined;
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
