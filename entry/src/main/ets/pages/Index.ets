import { calculateTax, TaxResult, SPECIAL_DEDUCTIONS, HOUSING_FUND_RATES } from '../common/TaxCalculator'
import { promptAction } from '@kit.ArkUI'
import { hilog } from '@kit.PerformanceAnalysisKit'

@Entry
@Component
struct Index {
  @State salaryText: string = ''
  @State socialBaseText: string = ''
  @State housingFundRate: number = 7
  @State deductions: SelectOption[] = SPECIAL_DEDUCTIONS.map(d => {
    return new SelectOption(d.name, d.amount.toString(), false)
  })
  @State hasCalculated: boolean = false
  @State calcVersion: number = 0
  @State result: TaxResult | null = null

  aboutToAppear(): void {
    hilog.info(0x0001, 'TaxCalc', 'Index aboutToAppear')
  }

  doCalculate(): void {
    try {
      const salary = parseFloat(this.salaryText)
      if (isNaN(salary) || salary <= 0) {
        promptAction.showToast({ message: '请输入有效的税前工资', duration: 2000 })
        return
      }
      const socialBase = parseFloat(this.socialBaseText) || 0
      const deductionTotal = this.deductions
        .filter(d => d.checked)
        .reduce((sum, d) => sum + parseFloat(d.value), 0)
      this.result = calculateTax(salary, this.housingFundRate, socialBase, deductionTotal)
      this.calcVersion++
      this.hasCalculated = true
    } catch (e) {
      hilog.error(0x0001, 'TaxCalc', `doCalculate error: ${JSON.stringify(e)}`)
      promptAction.showToast({ message: `计算出错: ${e}`, duration: 3000 })
    }
  }

  build() {
    Scroll() {
      Column({ space: 16 }) {
        Column() {
          Image($r('app.media.logo'))
            .width(120)
            .height(120)
            .objectFit(ImageFit.Contain)
        }
        .width('100%')
        .alignItems(HorizontalAlign.Center)
        .padding(20)
        .backgroundColor('#ffffff')
        .borderRadius(16)
        .margin({ top: 24 })

        Text('个税计算器')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1a1a2e')
          .width('100%')

        Text('2024版税率 · 七级超额累进')
          .fontSize(13)
          .fontColor('#9ca3af')
          .width('100%')

        this.inputCard('💰 税前月工资', '请输入税前月收入', '元', this.salaryText,
          (value: string) => { this.salaryText = value })

        Column() {
          Text('📋 社保与公积金')
            .fontSize(15)
            .fontWeight(FontWeight.Medium)
            .fontColor('#374151')
            .width('100%')
            .margin({ bottom: 12 })

          Row({ space: 8 }) {
            Text('社保缴费基数')
              .fontSize(14)
              .fontColor('#6b7280')
              .width(90)
            TextInput({ placeholder: '默认同税前工资', text: this.socialBaseText })
              .type(InputType.Number)
              .fontSize(14)
              .layoutWeight(1)
              .height(40)
              .backgroundColor('#f3f4f6')
              .borderRadius(8)
              .onChange((value: string) => { this.socialBaseText = value })
            Text('元')
              .fontSize(13)
              .fontColor('#9ca3af')
          }
          .width('100%')

          Text('个人缴纳 ≈ 养老8% + 医疗2%+3元 + 失业0.2%')
            .fontSize(11)
            .fontColor('#d1d5db')
            .margin({ top: 4 })

          Row({ space: 8 }) {
            Text('公积金比例')
              .fontSize(14)
              .fontColor('#6b7280')
              .width(90)
            Slider({
              min: 5,
              max: 12,
              value: this.housingFundRate,
              step: 1
            })
              .layoutWeight(1)
              .showTips(true, `${this.housingFundRate}%`)
              .onChange((value: number) => { this.housingFundRate = value })
            Text(`${this.housingFundRate}%`)
              .fontSize(14)
              .fontWeight(FontWeight.Medium)
              .fontColor('#6366f1')
              .width(36)
          }
          .width('100%')
          .margin({ top: 8 })
        }
        .width('100%')
        .padding(16)
        .backgroundColor('#ffffff')
        .borderRadius(12)

        Column() {
          Text('📝 专项附加扣除（多选）')
            .fontSize(15)
            .fontWeight(FontWeight.Medium)
            .fontColor('#374151')
            .width('100%')
            .margin({ bottom: 12 })

          Text('每项均为月度扣除额度')
            .fontSize(11)
            .fontColor('#d1d5db')
            .margin({ bottom: 8 })

          Column({ space: 8 }) {
            ForEach(this.deductions, (item: SelectOption, index: number) => {
              Row() {
                Checkbox()
                  .select(item.checked)
                  .selectedColor('#6366f1')
                  .onChange((value: boolean) => {
                    this.deductions[index].checked = value
                  })
                Text(item.name)
                  .fontSize(14)
                  .fontColor('#374151')
                  .margin({ left: 8 })
                Blank()
                Text(`${item.value}元/月`)
                  .fontSize(13)
                  .fontColor('#6366f1')
                  .fontWeight(FontWeight.Medium)
              }
              .width('100%')
            })
          }
        }
        .width('100%')
        .padding(16)
        .backgroundColor('#ffffff')
        .borderRadius(12)

        Button('📊 计算个税')
          .type(ButtonType.Capsule)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .backgroundColor('#6366f1')
          .fontColor(Color.White)
          .borderRadius(24)
          .height(48)
          .width('100%')
          .onClick(() => { this.doCalculate() })

        if (this.hasCalculated && this.result && this.calcVersion > 0) {
          Column({ space: 12 }) {
            Text('📊 计算结果')
              .fontSize(15)
              .fontWeight(FontWeight.Medium)
              .fontColor('#374151')
              .width('100%')

            Column() {
              Text('税后月收入')
                .fontSize(12)
                .fontColor('#9ca3af')
              Text(`${this.result!.salaryAfterTax.toFixed(2)}`)
                .fontSize(36)
                .fontWeight(FontWeight.Bold)
                .fontColor('#1a1a2e')
              Text('元')
                .fontSize(13)
                .fontColor('#9ca3af')
            }
            .width('100%')
            .alignItems(HorizontalAlign.Center)
            .padding({ top: 8, bottom: 8 })

            Divider()
              .color('#f3f4f6')

            this.resultRow('税前工资', `${this.result!.salaryBeforeTax} 元`)
            this.resultRow('五险一金', `- ${this.result!.fiveInsuranceTotal.toFixed(2)} 元`)
            this.resultRow('应纳税所得额', `${this.result!.taxableIncome.toFixed(2)} 元`)
            this.resultRow('适用税率', `${(this.result!.taxRate * 100).toFixed(0)}%`)
            this.resultRow('个人所得税', `- ${this.result!.incomeTax} 元`)
            this.resultRow('实际税负率', `${this.result!.effectiveRate.toFixed(2)}%`)

            Row({ space: 4 }) {
              Text('💵 税后到手')
                .fontSize(14)
                .fontColor('#374151')
              Blank()
              Text(`${this.result!.salaryAfterTax.toFixed(2)} 元`)
                .fontSize(16)
                .fontWeight(FontWeight.Bold)
                .fontColor('#6366f1')
            }
            .width('100%')
            .padding({ top: 8, bottom: 4 })

            if (this.result!.incomeTax === 0) {
              Text('🎉 无需缴纳个税')
                .fontSize(13)
                .fontColor('#10b981')
                .fontWeight(FontWeight.Medium)
            }
          }
          .width('100%')
          .padding(16)
          .backgroundColor('#ffffff')
          .borderRadius(12)
        }

        Row() {
          Text('口袋万物')
            .fontSize(12)
            .fontColor('#9ca3af')
          Text(' · ')
            .fontSize(12)
            .fontColor('#d1d5db')
          Text('www.koudai.cool')
            .fontSize(12)
            .fontColor('#6366f1')
        }
        .width('100%')
        .justifyContent(FlexAlign.Center)
        .padding({ top: 24, bottom: 32 })
      }
      .width('100%')
      .padding({ left: 16, right: 16 })
      .alignItems(HorizontalAlign.Start)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#fafbfc')
    .scrollBar(BarState.Off)
  }

  @Builder inputCard(label: string, placeholder: string, unit: string, value: string, onChange: (value: string) => void) {
    Column() {
      Text(label)
        .fontSize(15)
        .fontWeight(FontWeight.Medium)
        .fontColor('#374151')
        .width('100%')
        .margin({ bottom: 12 })
      Row({ space: 8 }) {
        TextInput({ placeholder: placeholder, text: value })
          .type(InputType.Number)
          .fontSize(16)
          .layoutWeight(1)
          .height(48)
          .backgroundColor('#ffffff')
          .borderRadius(8)
          .border({ width: 1, color: '#e5e7eb' })
          .padding({ left: 12, right: 12 })
          .onChange(onChange)
        Text(unit)
          .fontSize(14)
          .fontColor('#9ca3af')
      }
      .width('100%')
    }
    .width('100%')
    .padding(16)
    .backgroundColor('#ffffff')
    .borderRadius(12)
  }

  @Builder resultRow(label: string, value: string) {
    Row({ space: 4 }) {
      Text(label)
        .fontSize(13)
        .fontColor('#6b7280')
      Blank()
      Text(value)
        .fontSize(13)
        .fontColor('#374151')
    }
    .width('100%')
    .padding({ top: 2, bottom: 2 })
  }
}

@Observed
class SelectOption {
  name: string
  value: string
  checked: boolean

  constructor(name: string, value: string, checked: boolean) {
    this.name = name
    this.value = value
    this.checked = checked
  }
}
