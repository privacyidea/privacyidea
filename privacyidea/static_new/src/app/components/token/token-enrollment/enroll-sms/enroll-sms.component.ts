import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { SmsGatewayService } from '../../../../services/sms-gateway/sms-gateway.service';

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
  ],
  templateUrl: './enroll-sms.component.html',
  styleUrl: './enroll-sms.component.scss',
})
export class EnrollSmsComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'sms')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() smsGateway!: WritableSignal<string>;
  @Input() phoneNumber!: WritableSignal<string>;
  @Input() readNumberDynamically!: WritableSignal<boolean>;
  smsGatewayOptions = signal<string[]>([]);

  constructor(private smsGatewayService: SmsGatewayService) {}

  ngOnInit(): void {
    this.smsGatewayService.getSmsGatewayOptions().subscribe((response) => {
      const options = response.result.value
        ? Object.values(response.result.value).map((item: any) => item.name)
        : [];
      this.smsGatewayOptions.set(options);
    });
  }
}
