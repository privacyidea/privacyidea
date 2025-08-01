import { CommonModule } from '@angular/common';
import { Component, EventEmitter, inject, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { MatOptionModule } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { Observable, of } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import {
  YubikeyApiPayloadMapper,
  YubikeyEnrollmentData,
} from '../../../../mappers/token-api-payload/yubikey-token-api-payload.mapper';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';

@Component({
  selector: 'app-enroll-yubikey',
  templateUrl: './enroll-yubikey.component.html',
  styleUrls: ['./enroll-yubikey.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatOptionModule,
    MatSelect,
  ],
})
export class EnrollYubikeyComponent implements OnInit {
  protected readonly enrollmentMapper: YubikeyApiPayloadMapper = inject(
    YubikeyApiPayloadMapper,
  );
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  testYubiKeyControl = new FormControl('');
  otpKeyControl = new FormControl('', [
    Validators.required,
    Validators.minLength(32),
    Validators.maxLength(32),
  ]);
  otpLengthControl = new FormControl<number | null>(44, [Validators.required]);

  yubikeyForm = new FormGroup({
    testYubiKey: this.testYubiKeyControl,
    otpKey: this.otpKeyControl,
    otpLength: this.otpLengthControl,
  });

  text =
    this.tokenService.tokenTypeOptions().find((type) => type.key === 'yubikey')
      ?.text || 'The Yubikey token can be used in AES encryption mode...';

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      testYubiKey: this.testYubiKeyControl,
      otpKey: this.otpKeyControl,
      otpLength: this.otpLengthControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.yubikeyForm.invalid) {
      this.yubikeyForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: YubikeyEnrollmentData = {
      ...basicOptions,
      type: 'yubikey',
      otpKey: this.otpKeyControl.value,
      otpLength: this.otpLengthControl.value,
    };

    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
