import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { SmsGatewayService } from '../../../../services/sms-gateway/sms-gateway.service';
import { SystemService } from '../../../../services/system/system.service';

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
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'sms')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() smsGateway!: WritableSignal<string>;
  @Input() phoneNumber!: WritableSignal<string>;
  @Input() readNumberDynamically!: WritableSignal<boolean>;
  smsGatewayOptions = signal<string[]>([]);
  defaultSMSGatewayIsSet = signal(false);

  constructor(
    private smsGatewayService: SmsGatewayService,
    private systemService: SystemService,
  ) {}

  ngOnInit(): void {
    this.smsGatewayService.getSmsGatewayOptions().subscribe((response) => {
      const options = response.result.value
        ? Object.values(response.result.value).map((item: any) => item.name)
        : [];
      this.smsGatewayOptions.set(options);

      this.systemService.getSystemConfig().subscribe((response) => {
        const config = response?.result?.value;
        if (config && config['sms.identifier']) {
          this.defaultSMSGatewayIsSet.set(true);
          this.smsGateway.set(config['sms.identifier']);
        }
      });
    });
  }
}
