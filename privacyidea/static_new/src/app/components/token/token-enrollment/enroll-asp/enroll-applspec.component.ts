import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
import { ServiceIdService } from '../../../../services/service-id/service-id.service';
import { ErrorStateMatcher, MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { TokenService } from '../../../../services/token/token.service';

export class ApplspecErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value === '' : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

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
    MatError,
  ],
  templateUrl: './enroll-applspec.component.html',
  styleUrl: './enroll-applspec.component.scss',
})
export class EnrollApplspecComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'applspec')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() serviceId!: WritableSignal<string>;
  @Input() generateOnServer!: WritableSignal<boolean>;
  @Input() otpKey!: WritableSignal<string>;
  serviceIdOptions = signal<string[]>([]);
  applspecErrorStateMatcher = new ApplspecErrorStateMatcher();

  constructor(
    private serviceIdService: ServiceIdService,
    private tokenService: TokenService,
  ) {}

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
