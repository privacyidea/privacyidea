import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RadiusServerService } from '../../../../services/radius-server/radius-server.service';
import { SystemService } from '../../../../services/system/system.service';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-enroll-radius',
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    MatError,
  ],
  templateUrl: './enroll-radius.component.html',
  styleUrl: './enroll-radius.component.scss',
})
export class EnrollRadiusComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'radius')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() radiusUser!: WritableSignal<string>;
  @Input() radiusServerConfiguration!: WritableSignal<string>;
  @Input() checkPinLocally!: WritableSignal<boolean>;
  radiusServerConfigurationOptions = signal<string[]>([]);
  defaultRadiusServerIsSet = signal(false);

  constructor(
    private radiusServerService: RadiusServerService,
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.radiusServerService
      .getRadiusServerConfigurationOptions()
      .subscribe((response) => {
        const options = response.result.value
          ? Object.keys(response.result.value)
          : [];
        this.radiusServerConfigurationOptions.set(options);
      });

    this.systemService.getSystemConfig().subscribe((response) => {
      const config = response?.result?.value;
      if (config && config['radius.identifier']) {
        this.defaultRadiusServerIsSet.set(true);
        this.radiusServerConfiguration.set(config['radius.identifier']);
      }
    });
  }
}
