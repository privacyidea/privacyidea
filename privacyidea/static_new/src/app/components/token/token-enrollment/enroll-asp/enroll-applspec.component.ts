import {
  Component,
  computed,
  EventEmitter,
  Inject,
  OnInit,
  Output,
} from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
import { ErrorStateMatcher, MatOption } from '@angular/material/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatError, MatSelect } from '@angular/material/select';
import {
  ServiceIdService,
  ServiceIdServiceInterface,
} from '../../../../services/service-id/service-id.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { ApplspecApiPayloadMapper } from '../../../../mappers/token-api-payload/applspec-token-api-payload.mapper';

export interface ApplspecEnrollmentOptions extends TokenEnrollmentData {
  type: 'applspec';
  serviceId: string; // Keep original type
  generateOnServer: boolean; // Keep original type
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
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
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
    private enrollmentMapper: ApplspecApiPayloadMapper,
    @Inject(ServiceIdService)
    private serviceIdService: ServiceIdServiceInterface,
    @Inject(TokenService)
    private tokenService: TokenServiceInterface,
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
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.applspecForm.invalid) {
      this.applspecForm.markAllAsTouched();
      return of(null);
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
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
