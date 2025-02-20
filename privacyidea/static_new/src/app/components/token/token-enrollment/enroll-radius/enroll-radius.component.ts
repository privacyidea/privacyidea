import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { RadiusServerService } from '../../../../services/radius-server/radius-server.service';

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
  ],
  templateUrl: './enroll-radius.component.html',
  styleUrl: './enroll-radius.component.scss',
})
export class EnrollRadiusComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'radius')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() radiusServer!: WritableSignal<string>;
  @Input() radiusUser!: WritableSignal<string>;
  @Input() radiusServerConfiguration!: WritableSignal<string>;
  @Input() checkPinLocally!: WritableSignal<boolean>;
  radiusServerConfigurationOptions = signal<string[]>([]);

  constructor(private radiusServerService: RadiusServerService) {}

  ngOnInit(): void {
    this.radiusServerService
      .getRadiusServerConfigurationOptions()
      .subscribe((response) => {
        const options = response.result.value
          ? Object.keys(response.result.value)
          : [];
        this.radiusServerConfigurationOptions.set(options);
      });
  }
}
