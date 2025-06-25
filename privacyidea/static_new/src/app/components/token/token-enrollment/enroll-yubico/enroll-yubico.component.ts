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
import { SystemService } from '../../../../services/system/system.service';
import { ErrorStateMatcher } from '@angular/material/core';
import { MatError } from '@angular/material/select';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { YubicoApiPayloadMapper } from '../../../../mappers/token-api-payload/yubico-token-api-payload.mapper';

export interface YubicoEnrollmentOptions extends TokenEnrollmentData {
  type: 'yubico';
  yubicoIdentifier: string;
}

export class YubicoErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalidLength =
      control && control.value ? control.value.length !== 12 : true;
    return !!(control && invalidLength && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-yubico',
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatError,
  ],
  templateUrl: './enroll-yubico.component.html',
  styleUrl: './enroll-yubico.component.scss',
})
export class EnrollYubicoComponent implements OnInit {
  yubicoErrorStatematcher = new YubicoErrorStateMatcher();
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'yubico')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  yubikeyIdentifierControl = new FormControl<string>('', [
    Validators.required,
    Validators.minLength(12),
    Validators.maxLength(12),
  ]);

  yubicoForm = new FormGroup({
    yubikeyIdentifier: this.yubikeyIdentifierControl,
  });

  yubicoIsConfigured = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!(
      cfg?.['yubico.id'] &&
      cfg?.['yubico.url'] &&
      cfg?.['yubico.secret']
    );
  });

  constructor(
    private systemService: SystemService,
    private tokenService: TokenService,
    private enrollmentMapper: YubicoApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      yubikeyIdentifier: this.yubikeyIdentifierControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.yubicoForm.invalid) {
      this.yubicoForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: YubicoEnrollmentOptions = {
      ...basicOptions,
      type: 'yubico',
      yubicoIdentifier: this.yubikeyIdentifierControl.value ?? '',
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
