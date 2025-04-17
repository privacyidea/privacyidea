import {
  Component,
  Input,
  linkedSignal,
  signal,
  WritableSignal,
} from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  MatButtonToggle,
  MatButtonToggleGroup,
} from '@angular/material/button-toggle';
import { ErrorStateMatcher, MatOption } from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { CaConnectorService } from '../../../../services/ca-connector/ca-connector.service';
import { TokenService } from '../../../../services/token/token.service';

export class CaConnectorErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value === '' : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-certificate',
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    MatButtonToggleGroup,
    MatButtonToggle,
    FormsModule,
    MatOption,
    MatSelect,
    MatError,
  ],
  templateUrl: './enroll-certificate.component.html',
  styleUrl: './enroll-certificate.component.scss',
})
export class EnrollCertificateComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'certificate')?.text;

  caConnectorOptions = linkedSignal({
    source: this.caConnectorService.caConnectorServiceResource.value,
    computation: (data) => {
      const rawValue = data?.result?.value;
      return rawValue && typeof rawValue === 'object'
        ? Object.values(rawValue).map((option: any) => option.connectorname)
        : [];
    },
  });

  certTemplateOptions = linkedSignal({
    source: this.caConnectorService.caConnectorServiceResource.value,
    computation: (data) => {
      const rawValue = data?.result?.value;
      return Array.isArray(rawValue) && rawValue.length && rawValue[0].templates
        ? Object.keys(rawValue[0].templates)
        : [];
    },
  });
  @Input() caConnector!: WritableSignal<string>;
  @Input() certTemplate!: WritableSignal<string>;
  @Input() pem!: WritableSignal<string>;
  @Input() description!: WritableSignal<string>;
  intentionToggle = signal('generate');
  caConnectorErrorStateMatcher = new CaConnectorErrorStateMatcher();

  constructor(
    private caConnectorService: CaConnectorService,
    private tokenService: TokenService,
  ) {}
}
