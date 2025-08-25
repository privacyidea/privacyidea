import { ChangeDetectionStrategy, Component, computed, effect, inject, OnInit, output, Signal } from "@angular/core";
import {
  AbstractControl,
  FormControl,
  FormRecord,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn
} from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { Observable, of } from "rxjs";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { QuestionApiPayloadMapper } from "../../../../mappers/token-api-payload/question-token-api-payload.mapper";

export interface QuestionEnrollmentOptions extends TokenEnrollmentData {
  type: "question";
  answers: Record<string, string>;
}

@Component({
  selector: "app-enroll-question",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule, MatFormField, MatInput, MatLabel, MatError],
  templateUrl: "./enroll-question.component.html",
  styleUrl: "./enroll-question.component.scss",
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EnrollQuestionComponent implements OnInit {
  protected readonly enrollmentMapper: QuestionApiPayloadMapper = inject(QuestionApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);

  readonly configMinNumberOfAnswers: Signal<number> = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return cfg && cfg["question.num_answers"] ? parseInt(cfg["question.num_answers"], 10) : 0;
  });
  private readonly guardControl = new FormControl<boolean>(false, { nonNullable: true });
  additionalFormFieldsChange = output<{ [key: string]: FormControl<unknown> }>();
  clickEnrollChange = output<(basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>>();
  questionForm = new FormRecord<FormControl<string>>({});
  questionControlNames: string[] = [];
  configQuestions = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value || {};
    return Object.entries(cfg)
      .filter(([k]) => k.startsWith("question.question."))
      .map(([, v]) => ({ question: v as string }));
  });

  constructor() {
    effect(() => {
      if (this.configQuestions()) this.updateFormControls();
    });
    effect(() => {
      const min = this.configMinNumberOfAnswers();
      this.questionForm.setValidators(this.minAnswersValidator(min));
      this.guardControl.setValidators(this.minAnswersValidator(min));
      this.questionForm.updateValueAndValidity({ emitEvent: false });
      this.guardControl.updateValueAndValidity({ emitEvent: false });
    });
    this.questionForm.valueChanges.subscribe(() => {
      this.guardControl.updateValueAndValidity({ emitEvent: false });
    });
  }

  ngOnInit(): void {
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      return of(null);
    }

    const answers: Record<string, string> = {};
    this.configQuestions().forEach((q) => {
      const controlName = `answer_${q.question.replace(/\s+/g, "_")}`;
      if (this.questionForm.get(controlName)?.value !== "") {
        answers[q.question] = this.questionForm.get(controlName)?.value;
      }
    });
    const enrollmentData: QuestionEnrollmentOptions = { ...basicOptions, type: "question", answers };
    return this.tokenService.enrollToken({ data: enrollmentData, mapper: this.enrollmentMapper });
  };

  private answeredCount(): number {
    return Object.values(this.questionForm.controls).filter((c) => (c.value ?? "").toString().trim() !== "").length;
  }

  private minAnswersValidator(min: number): ValidatorFn {
    return (_: AbstractControl): ValidationErrors | null => {
      const count = this.answeredCount();
      return count >= min ? null : { minAnswers: { required: min, actual: count } };
    };
  }

  private updateFormControls(): void {
    Object.keys(this.questionForm.controls).forEach((key) => this.questionForm.removeControl(key));
    this.questionControlNames = [];
    this.configQuestions().forEach((q) => {
      const controlName = `answer_${q.question.replace(/\s+/g, "_")}`;
      this.questionControlNames.push(controlName);
      this.questionForm.addControl(controlName, new FormControl<string>("", { nonNullable: true }));
    });
    this.additionalFormFieldsChange.emit({ __questionsGuard: this.guardControl });
    this.questionForm.updateValueAndValidity({ emitEvent: false });
    this.guardControl.updateValueAndValidity({ emitEvent: false });
  }
}
