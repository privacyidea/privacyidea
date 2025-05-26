import {
  Component,
  computed,
  effect,
  Input,
  WritableSignal,
} from '@angular/core';
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
  standalone: true,
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
  radiusServerConfigurationOptions = computed(
    () =>
      this.radiusServerService
        .radiusServerConfigurations()
        ?.map((config) => config.name) ?? [],
  );

  defaultRadiusServerIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.['radius.identifier'];
  });

  constructor(
    private radiusServerService: RadiusServerService,
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {
    effect(() => {
      const id =
        this.systemService.systemConfigResource.value()?.result?.value?.[
          'radius.identifier'
        ];
      if (id) {
        this.radiusServerConfiguration.set(id);
      }
    });
  }
}
