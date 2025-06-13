import {
  Component,
  computed,
  effect,
  Input,
  OnInit,
  Output,
  EventEmitter,
  WritableSignal,
} from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { SmsGatewayService } from '../../../../services/sms-gateway/sms-gateway.service';
import { SystemService } from '../../../../services/system/system.service';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface SmsEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'sms';
  smsGateway: string;
  phoneNumber?: string; // Optional if readNumberDynamically is true
  readNumberDynamically: boolean;
}

@Component({
  selector: 'app-enroll-sms',
  standalone: true,
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatSelect,
    MatOption,
    MatHint,
    MatError,
  ],
  templateUrl: './enroll-sms.component.html',
  styleUrl: './enroll-sms.component.scss',
})
export class EnrollSmsComponent implements OnInit {
  text = this.tokenService.tokenTypeOptions().find((type) => type.key === 'sms')
    ?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  smsGatewayControl = new FormControl<string>('', [Validators.required]);
  phoneNumberControl = new FormControl<string>(''); // Validator is set dynamically
  readNumberDynamicallyControl = new FormControl<boolean>(false, [
    Validators.required,
  ]);

  smsForm = new FormGroup({
    smsGateway: this.smsGatewayControl,
    phoneNumber: this.phoneNumberControl,
    readNumberDynamically: this.readNumberDynamicallyControl,
  });
  // Options for the template
  smsGatewayOptions = computed(() => {
    const raw =
      this.smsGatewayService.smsGatewayResource.value()?.result?.value;
    return raw && Array.isArray(raw) ? raw.map((gw) => gw.name) : [];
  });

  defaultSMSGatewayIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.['sms.identifier'];
  });

  constructor(
    private smsGatewayService: SmsGatewayService,
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {
    effect(() => {
      const id =
        this.systemService.systemConfigResource.value()?.result?.value?.[
          'sms.identifier'
        ];
      if (id && this.smsGatewayControl.pristine) {
        this.smsGatewayControl.setValue(id);
      }
    });
  }

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      smsGateway: this.smsGatewayControl,
      phoneNumber: this.phoneNumberControl,
      readNumberDynamically: this.readNumberDynamicallyControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.readNumberDynamicallyControl.valueChanges.subscribe((dynamic) => {
      if (!dynamic) {
        this.phoneNumberControl.setValidators([Validators.required]);
      } else {
        this.phoneNumberControl.clearValidators();
      }
      this.phoneNumberControl.updateValueAndValidity();
    });
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.smsForm.invalid) {
      this.smsForm.markAllAsTouched();
      return undefined;
    }

    const enrollmentData: SmsEnrollmentOptions = {
      ...basicOptions,
      type: 'sms',
      smsGateway: this.smsGatewayControl.value ?? '',
      readNumberDynamically: !!this.readNumberDynamicallyControl.value,
    };

    if (!enrollmentData.readNumberDynamically) {
      enrollmentData.phoneNumber = this.phoneNumberControl.value ?? '';
    }

    return this.tokenService.enrollToken(enrollmentData);
  };
}
