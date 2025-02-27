import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
import { TokenComponent } from '../../token.component';
import { ServiceIdService } from '../../../../services/service-id/service-id.service';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';

@Component({
  selector: 'app-enroll-applspec',
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    MatCheckbox,
    FormsModule,
    MatOption,
    MatSelect,
  ],
  templateUrl: './enroll-applspec.component.html',
  styleUrl: './enroll-applspec.component.scss',
})
export class EnrollApplspecComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'applspec')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() serviceId!: WritableSignal<string>;
  @Input() generateOnServer!: WritableSignal<boolean>;
  @Input() otpKey!: WritableSignal<string>;
  serviceIdOptions = signal<string[]>([]);

  constructor(private serviceIdService: ServiceIdService) {}

  ngOnInit(): void {
    this.serviceIdService.getServiceIdOptions().subscribe((response) => {
      const rawValue = response?.result?.value;
      const options =
        rawValue && typeof rawValue === 'object'
          ? Object.keys(rawValue).map((option: any) => option)
          : [];
      this.serviceIdOptions.set(options);
    });
  }
}
