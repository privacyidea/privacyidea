import { Component, computed, Input, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import { TokenService } from '../../../../services/token/token.service';
import { BasicEnrollmentOptions } from '../../../../services/token/token.service';

export interface TiqrEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'tiqr';
  // Keine typspezifischen Felder für die Initialisierung über EnrollmentOptions
  // Die TIQR-spezifischen Daten (tiqr.infoUrl etc.) kommen aus der Systemkonfiguration
  // und werden nicht direkt als EnrollmentOptions übergeben.
}
@Component({
  selector: 'app-enroll-tiqr',
  imports: [ReactiveFormsModule, FormsModule],
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
