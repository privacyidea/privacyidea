import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface YubikeyEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'yubikey';
  otpKey: string | null;
  otpLength: number | null;
}

@Component({
  selector: 'app-enroll-yubikey',
  templateUrl: './enroll-yubikey.component.html',
  styleUrls: ['./enroll-yubikey.component.scss'], // If present
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    // Other modules
  ],
})
export class EnrollYubikeyComponent implements OnInit {
  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  testYubiKeyControl = new FormControl('');
  otpKeyControl = new FormControl('', [
    Validators.required,
    Validators.minLength(32),
    Validators.maxLength(32),
  ]);
  otpLengthControl = new FormControl<number | null>(44, [Validators.required]);

  // FormGroup for bundling and easier value monitoring
  yubikeyForm = new FormGroup({
    testYubiKey: this.testYubiKeyControl,
    otpKey: this.otpKeyControl,
    otpLength: this.otpLengthControl,
  });

  // Example text, if still needed and not coming from outside
  text =
    this.tokenService.tokenTypeOptions().find((type) => type.key === 'yubikey')
      ?.text || 'The Yubikey token can be used in AES encryption mode...';

  constructor(private tokenService: TokenService) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      testYubiKey: this.testYubiKeyControl,
      otpKey: this.otpKeyControl,
      otpLength: this.otpLengthControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.testYubiKeyControl.valueChanges.subscribe((value) => {
      if (value && value.length > 0) {
        this.otpLengthControl.setValue(value.length);
      }
    });
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (this.yubikeyForm.invalid) {
      this.yubikeyForm.markAllAsTouched();
      return undefined;
    }

    const enrollmentData: YubikeyEnrollmentOptions = {
      ...basicOptions,
      type: 'yubikey',
      otpKey: this.otpKeyControl.value,
      otpLength: this.otpLengthControl.value,
    };

    return this.tokenService.enrollToken(enrollmentData);
  };
}
