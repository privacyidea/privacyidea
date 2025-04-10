import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import { TokenService } from '../../../../services/token/token.service';

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
  defaultSMTPisSet = signal(false);

  constructor(
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.systemService.getSystemConfig().subscribe((response) => {
      const config = response?.result?.value;
      if (config && config['email.identifier']) {
        this.defaultSMTPisSet.set(true);
      }
    });
  }
}
