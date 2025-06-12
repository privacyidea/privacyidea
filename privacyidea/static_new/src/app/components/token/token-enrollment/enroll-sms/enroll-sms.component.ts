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
import { SmsGatewayService } from '../../../../services/sms-gateway/sms-gateway.service';
import { SystemService } from '../../../../services/system/system.service';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface SmsEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'sms';
  smsGateway: string;
  phoneNumber?: string; // Optional if readNumberDynamically is true
  readNumberDynamically: boolean;
}

@Component({
  selector: 'app-enroll-sms',
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatSelect,
    MatOption,
    MatHint,
    MatError,
  ],
  templateUrl: './enroll-sms.component.html',
  styleUrl: './enroll-sms.component.scss',
})
export class EnrollSmsComponent {
  text = this.tokenService.tokenTypeOptions().find((type) => type.key === 'sms')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() smsGateway!: WritableSignal<string>;
  @Input() phoneNumber!: WritableSignal<string>;
  @Input() readNumberDynamically!: WritableSignal<boolean>;

  smsGatewayOptions = computed(() => {
    const raw =
      this.smsGatewayService.smsGatewayResource.value()?.result?.value;
    return raw && Array.isArray(raw) ? raw.map((gw) => gw.name) : [];
  });

  defaultSMSGatewayIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!cfg?.['sms.identifier'];
  });

  constructor(
    private smsGatewayService: SmsGatewayService,
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {
    effect(() => {
      const id =
        this.systemService.systemConfigResource.value()?.result?.value?.[
          'sms.identifier'
        ];
      if (id) {
        this.smsGateway.set(id);
      }
    });
  }
}
