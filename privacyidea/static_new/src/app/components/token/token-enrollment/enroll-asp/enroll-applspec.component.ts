import {
  Component,
  computed,
  EventEmitter,
  OnInit,
  Output,
} from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
import { ServiceIdService } from '../../../../services/service-id/service-id.service';
import { ErrorStateMatcher, MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface ApplspecEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'applspec';
  serviceId: string;
  generateOnServer: boolean;
  otpKey?: string;
}

export class ApplspecErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value === '' : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-applspec',
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    MatCheckbox,
    FormsModule,
    MatOption,
    MatSelect,
    MatError,
  ],
  templateUrl: './enroll-applspec.component.html',
  styleUrl: './enroll-applspec.component.scss',
})
export class EnrollApplspecComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'applspec')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  serviceIdControl = new FormControl<string>('', [Validators.required]);
  generateOnServerControl = new FormControl<boolean>(true, [
    Validators.required,
  ]);
  otpKeyControl = new FormControl<string>(''); // Validator is set dynamically

  applspecForm = new FormGroup({
    serviceId: this.serviceIdControl,
    generateOnServer: this.generateOnServerControl,
    otpKey: this.otpKeyControl,
  });
  // Options for the template
  serviceIdOptions = computed(
    () => this.serviceIdService.serviceIds().map((s) => s.name) || [],
  );
  applspecErrorStateMatcher = new ApplspecErrorStateMatcher();

  constructor(
    private serviceIdService: ServiceIdService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      serviceId: this.serviceIdControl,
      generateOnServer: this.generateOnServerControl,
      otpKey: this.otpKeyControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.generateOnServerControl.valueChanges.subscribe((generate) => {
      if (!generate) {
        this.otpKeyControl.setValidators([Validators.required]);
      } else {
        this.otpKeyControl.clearValidators();
      }
      this.otpKeyControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.applspecForm.invalid) {
      this.applspecForm.markAllAsTouched();
      return undefined;
    }
    const enrollmentData: ApplspecEnrollmentOptions = {
      ...basicOptions,
      type: 'applspec',
      serviceId: this.serviceIdControl.value ?? '',
      generateOnServer: !!this.generateOnServerControl.value,
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyControl.value ?? '';
    }
    return this.tokenService.enrollToken(enrollmentData);
  };
}
