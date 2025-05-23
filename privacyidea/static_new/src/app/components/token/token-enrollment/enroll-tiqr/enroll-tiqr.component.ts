import { Component, computed, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-enroll-tiqr',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-tiqr.component.html',
  styleUrl: './enroll-tiqr.component.scss',
})
export class EnrollTiqrComponent {
  @Input() description!: WritableSignal<string>;
  defaultTiQRIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!(
      cfg?.['tiqr.infoUrl'] &&
      cfg?.['tiqr.logoUrl'] &&
      cfg?.['tiqr.regServer']
    );
  });

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'tiqr')?.text;

  constructor(
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {}
}
