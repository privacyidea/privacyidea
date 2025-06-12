import { Component, computed, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import { ErrorStateMatcher } from '@angular/material/core';
import { MatError } from '@angular/material/select';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface YubicoEnrollmentOptions extends BasicEnrollmentOptions {
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
export class EnrollYubicoComponent {
  @Input() description!: WritableSignal<string>;
  @Input() yubikeyIdentifier!: WritableSignal<string>;
  yubicoErrorStatematcher = new YubicoErrorStateMatcher();
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'yubico')?.text;

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
  ) {}
}
