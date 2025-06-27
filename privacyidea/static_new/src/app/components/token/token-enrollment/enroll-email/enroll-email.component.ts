import {
  Component,
  computed,
  EventEmitter,
  OnInit,
  Output,
} from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import { TokenService } from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { EmailApiPayloadMapper } from '../../../../mappers/token-api-payload/email-token-api-payload.mapper';

export interface EmailEnrollmentOptions extends TokenEnrollmentData {
  type: 'email';
  emailAddress?: string;
  readEmailDynamically: boolean; // Keep original type
}

@Component({
  selector: 'app-enroll-email',
  standalone: true,
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatError,
  ],
  templateUrl: './enroll-email.component.html',
  styleUrl: './enroll-email.component.scss',
})
export class EnrollEmailComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'email')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null> // Keep original type
  >();

  emailAddressControl = new FormControl<string>('', [Validators.email]); // Validator is set dynamically
  readEmailDynamicallyControl = new FormControl<boolean>(false, [
    Validators.required,
  ]);

  emailForm = new FormGroup({
    emailAddress: this.emailAddressControl,
    readEmailDynamically: this.readEmailDynamicallyControl,
  });

  // Options for the template
  defaultSMTPisSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.['email.identifier'];
  });

  constructor(
    private systemService: SystemService,
    private tokenService: TokenService,
    private enrollmentMapper: EmailApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      emailAddress: this.emailAddressControl,
      readEmailDynamically: this.readEmailDynamicallyControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.readEmailDynamicallyControl.valueChanges.subscribe((dynamic) => {
      // Keep original subscription
      this.emailAddressControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.emailForm.invalid) {
      this.emailForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: EmailEnrollmentOptions = {
      ...basicOptions,
      type: 'email',
      readEmailDynamically: !!this.readEmailDynamicallyControl.value, // Keep original logic
    };
    if (!enrollmentData.readEmailDynamically) {
      enrollmentData.emailAddress = this.emailAddressControl.value ?? '';
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    }); // Apply the requested change
  };
}
