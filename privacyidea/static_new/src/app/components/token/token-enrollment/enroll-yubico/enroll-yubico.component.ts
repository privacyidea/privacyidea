import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import { ErrorStateMatcher } from '@angular/material/core';
import { MatError } from '@angular/material/select';
import { TokenService } from '../../../../services/token/token.service';

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
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'yubico')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() yubikeyIdentifier!: WritableSignal<string>;
  yubicoIsConfigured = signal(false);
  yubicoErrorStatematcher = new YubicoErrorStateMatcher();

  constructor(
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.systemService.getSystemConfig().subscribe((response) => {
      const config = response?.result?.value;
      if (
        config &&
        config['yubico.id'] &&
        config['yubico.url'] &&
        config['yubico.secret']
      ) {
        this.yubicoIsConfigured.set(true);
      }
    });
  }
}
