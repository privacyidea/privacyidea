import { Component, computed, Input, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface EmailEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'email';
  emailAddress?: string; // Optional if readEmailDynamically is true
  readEmailDynamically: boolean;
}

@Component({
  selector: 'app-enroll-email',
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
export class EnrollEmailComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'email')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() emailAddress!: WritableSignal<string>;
  @Input() readEmailDynamically!: WritableSignal<boolean>;
  defaultSMTPisSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.['email.identifier'];
  });

  constructor(
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {}
}
