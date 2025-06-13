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
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface EmailEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'email';
  emailAddress?: string; // Optional if readEmailDynamically is true
  readEmailDynamically: boolean;
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
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
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
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      emailAddress: this.emailAddressControl,
      readEmailDynamically: this.readEmailDynamicallyControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.readEmailDynamicallyControl.valueChanges.subscribe((dynamic) => {
      if (!dynamic) {
        this.emailAddressControl.setValidators([
          Validators.required,
          Validators.email,
        ]);
      } else {
        this.emailAddressControl.clearValidators();
        this.emailAddressControl.setValidators([Validators.email]); // Keep email format validation
      }
      this.emailAddressControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.emailForm.invalid) {
      this.emailForm.markAllAsTouched();
      return undefined;
    }
    const enrollmentData: EmailEnrollmentOptions = {
      ...basicOptions,
      type: 'email',
      readEmailDynamically: !!this.readEmailDynamicallyControl.value,
    };
    if (!enrollmentData.readEmailDynamically) {
      enrollmentData.emailAddress = this.emailAddressControl.value ?? '';
    }
    return this.tokenService.enrollToken(enrollmentData);
  };
}
